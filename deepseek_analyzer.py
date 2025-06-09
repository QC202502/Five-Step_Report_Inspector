"""
五步法分析器 - DeepSeek版
使用DeepSeek API进行研报五步法分析
"""

import os
import json
import re
import tempfile
import subprocess
import requests  # 使用requests库直接调用API
from contextlib import contextmanager
import time
from datetime import datetime

class DeepSeekAnalyzer:
    """使用DeepSeek API进行研报五步法分析的分析器"""
    
    def __init__(self):
        """初始化DeepSeek分析器"""
        print("初始化DeepSeek五步法分析器")
        
        # 初始化API密钥
        self.api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not self.api_key:
            # 警告用户需要设置API密钥
            print("警告: 未设置DEEPSEEK_API_KEY环境变量，请在.env文件中设置或直接导出环境变量")
            self.api_key = "YOUR_DEEPSEEK_API_KEY"  # 使用占位符
        
        self.base_url = os.environ.get("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions")
        
        # 添加system_prompt属性
        self.system_prompt = "你是一个专业的投研助手，请使用黄燕铭五步分析法分析研报，并提供详细的分析结果。"
    
    def analyze_with_five_steps(self, report_title, report_content, industry=None):
        """
        使用DeepSeek对研报内容进行五步法分析
        
        Parameters:
        -----------
        report_title : str
            研报标题
        report_content : str
            研报内容正文
        industry : str, optional
            行业分类，用于提供更具针对性的分析
            
        Returns:
        --------
        dict
            包含五步法分析结果的字典，并包含完整的分析文本
        """
        try:
            # 使用DeepSeek进行分析
            analysis_text = self._ask_deepseek(report_title, report_content, industry)
            
            # 将文本分析结果转换为结构化数据
            structured_result = self._parse_analysis(analysis_text)
            
            # 确保原始分析文本被保存
            structured_result['full_analysis'] = analysis_text
            
            return structured_result
            
        except Exception as e:
            print(f"DeepSeek分析过程中出错: {str(e)}")
            # 出错时返回简单的分析结果
            return self._generate_fallback_analysis()
    
    def _ask_deepseek(self, report_title, report_content, industry=None):
        """
        向DeepSeek API发送请求并获取回复，添加重试机制
        """
        if not self.api_key:
            raise ValueError("DeepSeek API密钥未设置")
        
        url = "https://api.deepseek.com/v1/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 准备详细提示词
        industry_context = f"该研报属于{industry}行业" if industry else ""
        
        detailed_prompt = f"""
请使用黄燕铭五步分析法分析以下研报，并按照指定格式返回结果。

研报标题: {report_title}
{industry_context}

研报内容:
{report_content[:1000]}...

请严格按照以下格式提供分析:

## 体检清单
| 五步要素 | 是否覆盖 | 快评 |
| ------- | ------- | ---- |
| 信息 | [是/否] | [简要评价] |
| 逻辑 | [是/否] | [简要评价] |
| 超预期 | [是/否] | [简要评价] |
| 催化剂 | [是/否] | [简要评价] |
| 结论 | [是/否] | [简要评价] |

## 五步框架梳理
| 步骤 | 核心内容提炼 |
| ---- | ------------ |
| Information | [报告中的关键信息点] |
| Logic | [报告的逻辑推理链] |
| Beyond-Consensus | [超出市场预期的观点] |
| Catalyst | [报告中提到的催化剂] |
| Conclusion | [报告的主要结论] |

## 可操作补强思路
| 待完善点 | 建议 |
| ------- | ---- |
| [缺失点1] | [具体建议] |
| [缺失点2] | [具体建议] |
| [缺失点3] | [具体建议] |

## 一句话总结
[简明扼要的总体评价]

## 五步法定量评分
| 步骤 | 分数(0-100) | 评价 |
| ---- | ----------- | ---- |
| 信息 | [分数] | [简短评价] |
| 逻辑 | [分数] | [简短评价] |
| 超预期 | [分数] | [简短评价] |
| 催化剂 | [分数] | [简短评价] |
| 结论 | [分数] | [简短评价] |
| 总分 | [加权平均分] | [总体评价] |
"""
        
        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": detailed_prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 4000
        }
        
        print("正在使用 requests 库调用 DeepSeek API...")
        
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json=data,
                    timeout=60  # 增加超时时间
                )
                
                response.raise_for_status()  # 检查HTTP错误
                result = response.json()
                
                if "choices" in result and len(result["choices"]) > 0:
                    print("成功从DeepSeek API获取分析结果。")
                    return result["choices"][0]["message"]["content"]
                else:
                    print(f"DeepSeek API返回了意外的响应格式: {result}")
                    if attempt < max_retries - 1:
                        print(f"尝试重试 ({attempt+1}/{max_retries})...")
                        time.sleep(retry_delay)
                        continue
                    return "API返回了无效的响应格式。"
                
            except requests.exceptions.ChunkedEncodingError as e:
                print(f"连接中断错误 (尝试 {attempt+1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    print(f"等待 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                else:
                    print("达到最大重试次数，返回默认分析结果")
                    return self._generate_default_analysis()
            except requests.exceptions.RequestException as e:
                print(f"调用 DeepSeek API 时出错 (尝试 {attempt+1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    print(f"等待 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                else:
                    print("达到最大重试次数，返回默认分析结果")
                    return self._generate_default_analysis()
        
        return self._generate_default_analysis()
    
    def _parse_analysis(self, analysis_text):
        """
        将DeepSeek生成的文本分析结果解析为结构化数据
        """
        try:
            # 初始化结果结构
            result = {
                "analysis": {
                    "信息": {"found": False, "keywords": [], "evidence": [], "description": "", "step_score": 0},
                    "逻辑": {"found": False, "keywords": [], "evidence": [], "description": "", "step_score": 0},
                    "超预期": {"found": False, "keywords": [], "evidence": [], "description": "", "step_score": 0},
                    "催化剂": {"found": False, "keywords": [], "evidence": [], "description": "", "step_score": 0},
                    "结论": {"found": False, "keywords": [], "evidence": [], "description": "", "step_score": 0},
                    "summary": {"completeness_score": 0, "steps_found": 0, "evaluation": ""}
                },
                "full_analysis": analysis_text  # 保存完整的分析文本
            }
            
            # 尝试解析体检清单部分
            try:
                checklist_section = analysis_text.split("## 体检清单")[1].split("##")[0]
                steps = ["信息", "逻辑", "超预期", "催化剂", "结论"]
                
                for step in steps:
                    for line in checklist_section.split("\n"):
                        if step in line:
                            # 检查是否包含"✅"标记
                            if "✅" in line:
                                result["analysis"][step]["found"] = True
                                # 提取快评作为描述
                                match = re.search(r'\|.*\|.*\|(.*)\|', line)
                                if match:
                                    result["analysis"][step]["description"] = match.group(1).strip()
                            # 检查是否包含"⚠️"标记 (部分应用)
                            elif "⚠️" in line:
                                result["analysis"][step]["found"] = True
                                match = re.search(r'\|.*\|.*\|(.*)\|', line)
                                if match:
                                    result["analysis"][step]["description"] = match.group(1).strip()
            except Exception as e:
                print(f"解析体检清单时出错: {e}")
            
            # 解析五步框架梳理部分
            try:
                framework_section_match = re.search(r'## 五步框架梳理(.*?)##', analysis_text, re.DOTALL)
                if framework_section_match:
                    framework_section = framework_section_match.group(1)
                    steps_mapping = {
                        'Information': '信息',
                        'Logic': '逻辑',
                        'Beyond-Consensus': '超预期',
                        'Catalyst': '催化剂',
                        'Conclusion': '结论'
                    }
                    
                    for eng_name, cn_name in steps_mapping.items():
                        pattern = r'\| ' + re.escape(eng_name) + r' \|(.*?)\|'
                        match = re.search(pattern, framework_section, re.DOTALL)
                        if match and cn_name in result["analysis"]:
                            result["analysis"][cn_name]["framework_summary"] = match.group(1).strip()
            except Exception as e:
                print(f"解析五步框架梳理时出错: {e}")
            
            # 解析可操作补强思路部分
            try:
                suggestions_match = re.search(r'## 可操作补强思路(.*?)##', analysis_text, re.DOTALL)
                if suggestions_match:
                    improvement_suggestions = suggestions_match.group(1).strip()
                    result["analysis"]["improvement_suggestions"] = improvement_suggestions
            except Exception as e:
                print(f"解析可操作补强思路时出错: {e}")
            
            # 解析五步法定量评分部分
            try:
                scores_section = analysis_text.split("## 五步法定量评分")[1]
                steps = ["信息", "逻辑", "超预期", "催化剂", "结论"]
                total_score = 0
                steps_found = 0
                
                for step in steps:
                    for line in scores_section.split("\n"):
                        if line.strip().startswith(f"| {step}"):
                            parts = line.split("|")
                            if len(parts) >= 4:
                                try:
                                    score = int(parts[2].strip())
                                    result["analysis"][step]["step_score"] = score
                                    
                                    # 如果分数大于等于60，认为是有效应用
                                    if score >= 60:
                                        steps_found += 1
                                    
                                    total_score += score
                                    
                                    # 提取评价
                                    if len(parts) >= 5:
                                        # 如果描述为空，使用评价作为描述
                                        if not result["analysis"][step]["description"]:
                                            result["analysis"][step]["description"] = parts[3].strip()
                                except Exception as e:
                                    print(f"解析步骤'{step}'评分时出错: {e}")
                
                # 提取总分
                for line in scores_section.split("\n"):
                    if "总分" in line:
                        parts = line.split("|")
                        if len(parts) >= 4:
                            try:
                                overall_score = int(parts[2].strip())
                                result["analysis"]["summary"]["completeness_score"] = overall_score
                                
                                # 如果找到评价
                                if len(parts) >= 5:
                                    result["analysis"]["summary"]["evaluation"] = parts[3].strip()
                            except:
                                # 如果无法提取总分，使用平均分
                                if len(steps) > 0:
                                    avg_score = total_score // len(steps)
                                    result["analysis"]["summary"]["completeness_score"] = avg_score
                            break
                
                # 如果没有找到总分行
                if result["analysis"]["summary"]["completeness_score"] == 0 and len(steps) > 0:
                    avg_score = total_score // len(steps)
                    result["analysis"]["summary"]["completeness_score"] = avg_score
                
                result["analysis"]["summary"]["steps_found"] = steps_found
            except Exception as e:
                print(f"解析五步法定量评分时出错: {e}")
            
            # 如果没有评价，根据分数生成评价
            if not result["analysis"]["summary"]["evaluation"]:
                score = result["analysis"]["summary"]["completeness_score"]
                result["analysis"]["summary"]["evaluation"] = self._get_evaluation_from_score(score)
            
            # 尝试提取一句话总结
            try:
                summary_section_match = re.search(r'## 一句话总结(.*?)##', analysis_text, re.DOTALL)
                if summary_section_match:
                    one_line_summary = summary_section_match.group(1).strip()
                    result["analysis"]["summary"]["one_line_summary"] = one_line_summary
                else:
                    result["analysis"]["summary"]["one_line_summary"] = "无法提取一句话总结"
            except Exception as e:
                print(f"提取一句话总结时出错: {e}")
                result["analysis"]["summary"]["one_line_summary"] = "无法提取一句话总结"
            
            return result
            
        except Exception as e:
            print(f"解析DeepSeek分析结果时出错: {str(e)}")
            return self._generate_fallback_analysis()
    
    def _generate_fallback_analysis(self):
        """生成后备分析结果，当分析失败时使用"""
        return {
            "analysis": {
                "信息": {"found": True, "keywords": ["数据"], "evidence": [], "description": "包含基本信息", "step_score": 50},
                "逻辑": {"found": True, "keywords": ["分析"], "evidence": [], "description": "包含基本逻辑", "step_score": 50},
                "超预期": {"found": False, "keywords": [], "evidence": [], "description": "未找到明显超预期", "step_score": 0},
                "催化剂": {"found": False, "keywords": [], "evidence": [], "description": "未找到明显催化剂", "step_score": 0},
                "结论": {"found": True, "keywords": ["建议"], "evidence": [], "description": "包含基本结论", "step_score": 50},
                "summary": {
                    "completeness_score": 30,
                    "steps_found": 3,
                    "evaluation": "研报部分应用了五步分析法，关键分析要素有所欠缺",
                    "one_line_summary": "分析过程中出现错误，无法获取详细分析"
                }
            },
            "full_analysis": "无法获取DeepSeek分析结果"
        }
    
    def _get_evaluation_from_score(self, score):
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
    
    def _generate_default_analysis(self):
        """当API调用失败时生成默认的分析结果"""
        print("生成默认分析结果...")
        return json.dumps({
            "analysis": {
                "信息": {
                    "found": True,
                    "keywords": ["信息", "数据"],
                    "evidence": ["由于API连接问题，无法获取详细分析"],
                    "description": "收集和整理相关信息，包括公司公告、行业数据、政策变化等"
                },
                "逻辑": {
                    "found": True,
                    "keywords": ["分析", "推理"],
                    "evidence": ["由于API连接问题，无法获取详细分析"],
                    "description": "基于信息进行分析推理，形成对市场或个股的基本判断"
                },
                "超预期": {
                    "found": False,
                    "keywords": [],
                    "evidence": [],
                    "description": "寻找市场共识之外的信息点，发现被低估或高估的因素"
                },
                "催化剂": {
                    "found": False,
                    "keywords": [],
                    "evidence": [],
                    "description": "找出能够促使价格变动的关键事件或因素"
                },
                "结论": {
                    "found": True,
                    "keywords": ["建议", "结论"],
                    "evidence": ["由于API连接问题，无法获取详细分析"],
                    "description": "给出明确的投资建议，包括评级、目标价等"
                },
                "summary": {
                    "completeness_score": 60,
                    "steps_found": 3,
                    "evaluation": "研报部分应用了五步分析法，关键分析要素有所欠缺"
                }
            }
        })

    def parse_five_step_scores(self, analysis_text):
        """
        从分析文本中解析五步法定量评分
        添加更健壮的错误处理
        """
        try:
            # 尝试解析JSON
            analysis_data = json.loads(analysis_text)
            
            # 检查分析数据结构
            if "analysis" not in analysis_data:
                print("警告: 分析结果中没有'analysis'键")
                return {
                    "completeness_score": 0,
                    "steps_found": 0,
                    "evaluation": "无法解析分析结果"
                }
            
            analysis = analysis_data["analysis"]
            
            # 检查是否已经有summary
            if "summary" in analysis:
                return analysis["summary"]
            
            # 计算找到的步骤数量
            steps_found = sum(1 for step in ["信息", "逻辑", "超预期", "催化剂", "结论"] 
                              if step in analysis and analysis[step].get("found", False))
            
            # 计算完整度分数
            completeness_score = int((steps_found / 5) * 100)
            
            # 生成评价文本
            if completeness_score >= 90:
                evaluation = "研报非常完整地应用了五步分析法，包含了全面的分析要素"
            elif completeness_score >= 80:
                evaluation = "研报较好地应用了五步分析法，大部分分析要素齐全"
            elif completeness_score >= 60:
                evaluation = "研报部分应用了五步分析法，关键分析要素有所欠缺"
            elif completeness_score >= 40:
                evaluation = "研报仅包含少量五步分析法要素，分析不够全面"
            else:
                evaluation = "研报几乎未应用五步分析法，分析要素严重不足"
            
            return {
                "completeness_score": completeness_score,
                "steps_found": steps_found,
                "evaluation": evaluation
            }
        except json.JSONDecodeError:
            print("警告: 无法解析JSON格式的分析结果")
            return {
                "completeness_score": 0,
                "steps_found": 0,
                "evaluation": "无法解析分析结果"
            }
        except Exception as e:
            print(f"解析五步法定量评分时出错: {str(e)}")
            return {
                "completeness_score": 0,
                "steps_found": 0,
                "evaluation": "解析分析结果时出错"
            }

    def generate_video_script(self, report_info, analysis_result):
        """
        生成适合投资顾问口播或短视频的文案
        
        Parameters:
        -----------
        report_info : dict
            研报基本信息，包含标题、日期、机构等
        analysis_result : dict
            五步法分析结果
            
        Returns:
        --------
        str
            生成的视频文案
        """
        try:
            # 检查API密钥是否可用
            api_key = os.environ.get('DEEPSEEK_API_KEY')
            if not api_key:
                try:
                    from dotenv import load_dotenv
                    load_dotenv()
                    api_key = os.environ.get('DEEPSEEK_API_KEY')
                except ImportError:
                    pass
            
            # 如果API密钥不可用，返回错误信息
            if not api_key:
                print("错误: API密钥不可用，无法生成视频文案")
                return "错误: 无法生成视频文案。请先配置DeepSeek API密钥。您可以在.env文件中设置DEEPSEEK_API_KEY环境变量，或直接在系统中设置该环境变量。"
            
            # 提取需要的信息
            title = report_info.get('title', '未知研报')
            date = report_info.get('date', '未知日期')
            org = report_info.get('org', '未知机构')
            industry = report_info.get('industry', '未知行业')
            rating = report_info.get('rating', '未知评级')
            
            # 获取五步法分析内容
            steps = analysis_result.get('analysis', {})
            info_summary = steps.get('信息', {}).get('framework_summary', '暂无信息梳理')
            logic_summary = steps.get('逻辑', {}).get('framework_summary', '暂无逻辑梳理')
            beyond_summary = steps.get('超预期', {}).get('framework_summary', '暂无超预期分析')
            catalyst_summary = steps.get('催化剂', {}).get('framework_summary', '暂无催化剂分析')
            conclusion_summary = steps.get('结论', {}).get('framework_summary', '暂无结论梳理')
            
            # 整体评分
            score = analysis_result.get('analysis', {}).get('summary', {}).get('completeness_score', 0)
            
            # 生成视频文案的DeepSeek提示词
            prompt = f"""请基于以下研报信息和五步法分析结果，生成一段详细、流畅的投资顾问口播文案，确保五个维度都得到充分展示。

研报基本信息:
- 标题: {title}
- 发布日期: {date}
- 发布机构: {org}
- 行业: {industry}
- 评级: {rating}

研报五步法分析内容:
- 信息梳理: {info_summary}
- 逻辑框架: {logic_summary}
- 超预期分析: {beyond_summary}
- 催化剂: {catalyst_summary}
- 结论: {conclusion_summary}

请生成一段详细、连贯的口播文案，满足以下要求:
1. 以投资顾问的视角解读这份研究报告，而非以研究员身份撰写
2. 开场白应明确提及这是对某机构研报的解读（例如："今天为大家解读一份来自{org}的研报..."）
3. 按照五步法顺序组织内容，确保每个维度都有足够篇幅展示
4. 在讲解过程中要明确区分"研报观点"和"我们的观点"，适当引用研报内容
5. 详细介绍研报中的核心信息和关键数据点
6. 清晰解释研报提出的投资逻辑和因果关系链
7. 具体说明研报中的超预期因素，并可以加入自己的专业判断
8. 详细列举研报提到的未来可能催化剂事件
9. 在结尾部分可以对研报结论做出评价，并给出自己的投资建议

语言要求：
- 采用中文，句子简洁清晰但信息量充足
- 使用自然流畅的口语化表达，适合朗读
- 使用第一人称，如"我们认为..."
- 段落之间要有自然过渡
- 总字数控制在700-900字
- 使用中文标点

请确保五步法的每个维度都有充分展示，不要简化或省略任何关键信息。直接给出文案内容，不要添加任何额外的解释或标题。"""

            # 调用DeepSeek API生成文案
            video_script = self._ask_deepseek_for_script(prompt)
            return video_script
            
        except Exception as e:
            print(f"生成视频文案时出错: {str(e)}")
            return f"生成视频文案失败: {str(e)}"
    
    def _ask_deepseek_for_script(self, prompt):
        """
        调用DeepSeek API生成视频文案
        
        Parameters:
        -----------
        prompt : str
            生成视频文案的提示词
            
        Returns:
        --------
        str
            生成的视频文案
        """
        # 获取API密钥
        api_key = os.environ.get('DEEPSEEK_API_KEY')
        if not api_key:
            print("警告: 未设置DEEPSEEK_API_KEY环境变量")
            # 尝试从配置文件获取
            try:
                from dotenv import load_dotenv
                load_dotenv()
                api_key = os.environ.get('DEEPSEEK_API_KEY')
            except ImportError:
                print("提示: 未安装python-dotenv, 无法从.env文件加载配置")
            
            if not api_key:
                print("错误: 无法获取DEEPSEEK_API_KEY，请设置环境变量或在.env文件中配置")
                return "无法生成视频文案: API密钥未配置"
        
        data = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "system", 
                    "content": "你是一位专业的投资顾问，擅长解读和评价其他机构发布的研究报告，并将其转化为详细、流畅的口播文案。你需要站在投资顾问的角度，而非研究员的角度，清晰区分研报观点和你自己的专业判断。确保五步法分析（信息、逻辑、超预期、催化剂、结论）的每个维度都得到充分展示，同时保持语言通俗易懂，适合向客户传达核心投资观点。"
                },
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.5,  # 适中的温度，平衡创造性和准确性
            "max_tokens": 2000,   # 增加token数量以支持更长的文案
            "top_p": 0.95         # 略微提高多样性
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                print("正在调用DeepSeek API生成视频文案...")
                response = requests.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=45  # 增加超时时间以处理更长的响应
                )
                
                response.raise_for_status()
                result = response.json()
                
                # 提取生成的文案
                generated_text = result["choices"][0]["message"]["content"]
                print(f"成功获取文案，长度: {len(generated_text)}字符")
                
                # 处理生成的文案，确保格式符合要求
                processed_text = self._process_generated_script(generated_text)
                
                return processed_text
                
            except requests.exceptions.RequestException as e:
                print(f"调用 DeepSeek API 生成视频文案时出错 (尝试 {attempt+1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    print(f"等待 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                else:
                    print("达到最大重试次数，返回错误信息")
                    return "很抱歉，目前无法生成视频文案。请稍后再试或联系系统管理员。"
        
        return "很抱歉，目前无法生成视频文案。请稍后再试或联系系统管理员。"
        
    def _process_generated_script(self, text):
        """
        处理生成的文案，确保格式符合要求
        
        Parameters:
        -----------
        text : str
            生成的原始文案
            
        Returns:
        --------
        str
            处理后的文案
        """
        # 移除可能的标题行或前言
        lines = text.strip().split('\n')
        
        # 移除可能的引号包裹
        text = text.strip('"\'')
        
        # 移除可能的标题行
        if len(lines) > 1 and (lines[0].startswith('# ') or '文案' in lines[0] or '脚本' in lines[0] or '：' in lines[0]):
            text = '\n'.join(lines[1:])
        
        # 合并多个空行为单个空行
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # 确保文案不超过字数限制
        words = text.replace('\n', '').replace(' ', '')
        if len(words) > 1000:  # 给予一些余量
            print(f"警告: 生成的文案超过字数限制 ({len(words)}字)，将进行截断")
            
            # 尝试在句子结束处截断
            sentences = re.split(r'([。！？])', text)
            truncated_text = ""
            char_count = 0
            
            for i in range(0, len(sentences), 2):
                if i+1 < len(sentences):
                    sentence = sentences[i] + sentences[i+1]
                else:
                    sentence = sentences[i]
                    
                if char_count + len(sentence.replace('\n', '').replace(' ', '')) <= 900:
                    truncated_text += sentence
                    char_count += len(sentence.replace('\n', '').replace(' ', ''))
                else:
                    break
            
            text = truncated_text
            
            # 确保文本以句号结尾
            if not text.strip().endswith(('。', '！', '？')):
                text = text.strip() + '。'
        
        # 检查是否包含五步法的关键内容
        key_dimensions = {
            '信息': ['数据', '信息', '行业现状', '公司表现', '核心数据'],
            '逻辑': ['逻辑', '因果关系', '发展路径', '投资机会'],
            '超预期': ['超预期', '超出预期', '超出市场预期', '市场预期'],
            '催化剂': ['催化剂', '触发因素', '关键事件'],
            '结论': ['结论', '评级', '推荐', '投资建议']
        }
        
        missing_dimensions = []
        
        for dimension, keywords in key_dimensions.items():
            dimension_found = False
            for keyword in keywords:
                if keyword in text:
                    dimension_found = True
                    break
            
            if not dimension_found:
                missing_dimensions.append(dimension)
        
        if missing_dimensions:
            print(f"警告: 生成的文案缺少以下维度: {', '.join(missing_dimensions)}")
        
        return text.strip() 