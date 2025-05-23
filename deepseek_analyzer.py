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
        使用 requests 库直接调用 DeepSeek API 进行实时分析
        """
        try:
            # 检查API密钥是否有效
            if not self.api_key or self.api_key == "YOUR_DEEPSEEK_API_KEY":
                print("警告: DeepSeek API Key 未正确配置。请设置环境变量 DEEPSEEK_API_KEY 或在.env文件中配置。")
                return (
                    "## 体检清单\n| 五步要素 | 是否覆盖 | 快评 |\n| --- | --- | --- |\n"
                    "| 信息 | ❌ | DeepSeek API Key未配置 |\n"
                    "## 五步框架梳理\n| 步骤 | 核心内容提炼 |\n| --- | --- |\n"
                    "| Information | [DeepSeek API Key未配置] |\n"
                    "## 一句话总结\n[DeepSeek API Key未配置，无法生成总结]\n"
                    "## 五步法定量评分\n| 步骤 | 分数(0-100) | 评价 |\n| --- | --- | --- |\n"
                    "| 信息 | 0 | API Key未配置 |"
                )

            print(f"正在使用 requests 库调用 DeepSeek API...")
            
            # 使用 requests 库调用 DeepSeek API
            model_name = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
            
            # 准备请求头
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 准备请求体
            industry_context = f"该研报属于{industry}行业" if industry else ""
            
            # 详细提示词，要求按特定格式返回
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
                "model": model_name,
                "messages": [
                    {"role": "system", "content": "你是一个专业的投研助手，请严格按照指定格式回答。"},
                    {"role": "user", "content": detailed_prompt}
                ],
                "temperature": 0.7
            }
            
            # 发送请求
            response = requests.post(
                self.base_url,
                headers=headers,
                json=data,
                timeout=120
            )
            
            # 检查响应状态
            response.raise_for_status()
            
            # 解析响应
            result = response.json()
            
            # 提取内容
            if "choices" in result and len(result["choices"]) > 0 and "message" in result["choices"][0] and "content" in result["choices"][0]["message"]:
                analysis_text = result["choices"][0]["message"]["content"]
                print("成功从DeepSeek API获取分析结果。")
                return analysis_text
            else:
                error_message = f"DeepSeek API返回格式不符合预期: {json.dumps(result, ensure_ascii=False)}"
                print(error_message)
                raise ValueError(error_message)
            
        except Exception as e:
            print(f"调用 DeepSeek API 或处理响应时出错: {str(e)}")
            import traceback
            traceback.print_exc()  # 打印详细的堆栈跟踪
            return "## 体检清单\n| 五步要素 | 是否覆盖 | 快评 |\n| --- | --- | --- |\n| 信息 | ❌ | API调用错误 |\n## 一句话总结\n[API调用错误，无法生成分析]"
    
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