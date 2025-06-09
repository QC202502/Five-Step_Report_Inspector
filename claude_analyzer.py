"""
五步法分析器 - DeepSeek版
使用DeepSeek API进行研报五步法分析
"""

import os
import json
import re
import tempfile
import subprocess
import requests  # 添加 requests 库用于调用 DeepSeek API
from contextlib import contextmanager

class DeepSeekAnalyzer:
    """使用DeepSeek API进行研报五步法分析的分析器"""
    
    def __init__(self):
        """初始化DeepSeek分析器"""
        print("初始化DeepSeek五步法分析器")
    
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
        # 构建提示词
        prompt = self._build_five_step_prompt(report_title, report_content, industry)
        
        try:
            # 使用DeepSeek进行分析
            analysis_text = self._ask_deepseek(prompt)
            
            # 将文本分析结果转换为结构化数据
            structured_result = self._parse_analysis(analysis_text)
            
            # 确保原始分析文本被保存
            structured_result['full_analysis'] = analysis_text
            
            return structured_result
            
        except Exception as e:
            print(f"DeepSeek分析过程中出错: {str(e)}")
            # 出错时返回简单的分析结果
            return self._generate_fallback_analysis()
    
    def _build_five_step_prompt(self, title, content, industry=None):
        """构建五步法分析的提示词"""
        industry_context = f"该研报属于{industry}行业，" if industry else ""
        
        # 不再限制内容长度，让模型自己处理
        
        prompt = f"""
请对以下研究报告使用黄燕铭五步分析法进行详细分析，并生成结构化评估：

报告标题: {title}
{industry_context}

报告内容:
{content}

请按以下格式提供分析:

## 体检清单
| 五步要素 | 是否覆盖 | 快评 |
| ------- | ------- | ---- |
| 信息 | [✅/⚠️/❌] | [简要评价] |
| 逻辑 | [✅/⚠️/❌] | [简要评价] |
| 超预期 | [✅/⚠️/❌] | [简要评价] |
| 催化剂 | [✅/⚠️/❌] | [简要评价] |
| 结论 | [✅/⚠️/❌] | [简要评价] |

## 五步框架梳理
| 步骤 | 核心内容提炼 |
| ---- | ------------ |
| Information | [报告中的关键信息点] |
| Logic | [报告的逻辑推理链] |
| Beyond-Consensus | [超出市场预期的观点，并指出缺口] |
| Catalyst | [报告中提到的催化剂，并指出缺口] |
| Conclusion | [报告的主要结论，并指出缺口] |

## 可操作补强思路
| 待完善点 | 建议 |
| ------- | ---- |
| [缺失点1] | [具体建议] |
| [缺失点2] | [具体建议] |
| [缺失点3] | [具体建议] |

## 一句话总结
[简明扼要的总体评价，包括优点和不足]

## 五步法定量评分
| 步骤 | 分数(0-100) | 评价 |
| ---- | ----------- | ---- |
| 信息 | [分数] | [简短评价] |
| 逻辑 | [分数] | [简短评价] |
| 超预期 | [分数] | [简短评价] |
| 催化剂 | [分数] | [简短评价] |
| 结论 | [分数] | [简短评价] |
| 总分 | [加权平均分] | [总体评价] |

请确保分析全面、客观，并针对研报的具体内容给出实质性的建议。
分数评定标准：80-100分为优秀，60-79分为良好，40-59分为一般，0-39分为不足。
        """
        
        return prompt
    
    def _ask_deepseek(self, prompt):
        """
        使用 DeepSeek API 进行实时分析
        """
        try:
            api_url = os.environ.get("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions")
            api_key = os.environ.get("DEEPSEEK_API_KEY")

            # 如果环境变量中没有API密钥，使用硬编码的值（需要修改为您的实际API密钥）
            if not api_key:
                api_key = "YOUR_DEEPSEEK_API_KEY"  # 请替换为您的真实DeepSeek API Key
            
            # 检查API密钥是否仍然是占位符
            if api_key == "YOUR_DEEPSEEK_API_KEY":
                print("警告: DeepSeek API Key 未配置。请设置环境变量 DEEPSEEK_API_KEY 或直接在代码中替换占位符。")
                return (
                    "## 体检清单\n| 五步要素 | 是否覆盖 | 快评 |\n| --- | --- | --- |\n"
                    "| 信息 | ❌ | DeepSeek API Key未配置 |\n"
                    "## 五步框架梳理\n| 步骤 | 核心内容提炼 |\n| --- | --- |\n"
                    "| Information | [DeepSeek API Key未配置] |\n"
                    "## 一句话总结\n[DeepSeek API Key未配置，无法生成总结]\n"
                    "## 五步法定量评分\n| 步骤 | 分数(0-100) | 评价 |\n| --- | --- | --- |\n"
                    "| 信息 | 0 | API Key未配置 |"
                )

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            model_name = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")  # 可通过环境变量指定模型

            data = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": "你是一个专业的投研助手，请严格按照五步法结构化分析研报。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7
            }
            
            print(f"正在向 DeepSeek API 发送请求 (模型: {model_name})...")
            
            response = requests.post(api_url, headers=headers, json=data, timeout=120)
            response.raise_for_status()  # 如果HTTP响应状态码不是200，引发异常
            
            result = response.json()
            
            # 解析返回内容
            if "choices" in result and len(result["choices"]) > 0 and "message" in result["choices"][0] and "content" in result["choices"][0]["message"]:
                analysis_text = result["choices"][0]["message"]["content"]
                print("成功从DeepSeek API获取分析结果。")
                return analysis_text
            else:
                error_message = f"DeepSeek API返回格式不符合预期: {json.dumps(result, ensure_ascii=False)}"
                print(error_message)
                raise ValueError(error_message)
            
        except requests.exceptions.Timeout:
            print("调用 DeepSeek API 超时")
            return self._generate_fallback_analysis().get('full_analysis', "分析失败(API超时)，请检查网络")
        except requests.exceptions.RequestException as e:
            print(f"调用 DeepSeek API 时发生网络错误: {str(e)}")
            return self._generate_fallback_analysis().get('full_analysis', "分析失败(网络错误)，请检查API调用和网络连接")
        except Exception as e:
            print(f"调用 DeepSeek API 或处理响应时出错: {str(e)}")
            return self._generate_fallback_analysis().get('full_analysis', "分析失败，请检查API调用和错误日志")
    
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
                                    description = match.group(1).strip()
                                    # 处理<br>标签，确保它们正确显示
                                    description = description.replace('<br>', '<br />')
                                    result["analysis"][step]["description"] = description
                            # 检查是否包含"⚠️"标记 (部分应用)
                            elif "⚠️" in line:
                                result["analysis"][step]["found"] = True
                                match = re.search(r'\|.*\|.*\|(.*)\|', line)
                                if match:
                                    description = match.group(1).strip()
                                    # 处理<br>标签，确保它们正确显示
                                    description = description.replace('<br>', '<br />')
                                    result["analysis"][step]["description"] = description
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
                            framework_summary = match.group(1).strip()
                            # 处理<br>标签，确保它们正确显示
                            framework_summary = framework_summary.replace('<br>', '<br />')
                            result["analysis"][cn_name]["framework_summary"] = framework_summary
            except Exception as e:
                print(f"解析五步框架梳理时出错: {e}")
            
            # 解析可操作补强思路部分
            try:
                suggestions_match = re.search(r'## 可操作补强思路(.*?)##', analysis_text, re.DOTALL)
                if suggestions_match:
                    improvement_suggestions = suggestions_match.group(1).strip()
                    # 检查是否为有效的改进建议内容
                    if improvement_suggestions and not improvement_suggestions.startswith('-------'):
                        result["analysis"]["improvement_suggestions"] = improvement_suggestions
                    else:
                        # 如果内容无效，使用默认的改进建议
                        result["analysis"]["improvement_suggestions"] = "| 整体完善 | 建议根据五步法框架进一步完善研报结构 |"
                else:
                    # 如果没有找到改进建议部分，使用默认的改进建议
                    result["analysis"]["improvement_suggestions"] = "| 整体完善 | 建议根据五步法框架进一步完善研报结构 |"
            except Exception as e:
                print(f"解析可操作补强思路时出错: {e}")
                # 出错时使用默认的改进建议
                result["analysis"]["improvement_suggestions"] = "| 整体完善 | 建议根据五步法框架进一步完善研报结构 |"
            
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
                                        # 如果找到评价
                                        if len(parts) >= 5:
                                            evaluation = parts[3].strip()
                                            # 处理<br>标签，确保它们正确显示
                                            evaluation = evaluation.replace('<br>', '<br />')
                                            result["analysis"][step]["description"] = evaluation
                                            result["analysis"]["summary"]["evaluation"] = evaluation
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
                                    evaluation = parts[3].strip()
                                    # 处理<br>标签，确保它们正确显示
                                    evaluation = evaluation.replace('<br>', '<br />')
                                    result["analysis"]["summary"]["evaluation"] = evaluation
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
                    # 处理<br>标签，确保它们正确显示
                    one_line_summary = one_line_summary.replace('<br>', '<br />')
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