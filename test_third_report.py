#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试脚本：用于测试 DeepSeekAnalyzer 分析医药行业研报
"""

from deepseek_analyzer import DeepSeekAnalyzer
import json

def main():
    print("开始测试 DeepSeekAnalyzer 分析医药行业研报...")
    
    # 创建分析器实例
    analyzer = DeepSeekAnalyzer()
    
    # 医药行业研报内容
    report_title = "医药行业深度报告：创新药研发进展与投资机会"
    report_content = """
摘要：
本报告对医药行业创新药研发现状进行深入分析，重点关注肿瘤免疫治疗、基因治疗等前沿领域的技术进展与商业化前景。我们认为，随着医保支付体系改革深化和创新药审批加速，国产创新药将迎来重要发展机遇。

一、行业现状分析
2024年以来，医药行业整体估值处于历史较低水平，但创新药板块表现相对强势。随着医保谈判常态化和集采范围扩大，仿制药利润空间持续收窄，而创新药企业的研发投入和产品管线却在不断丰富。截至2025年第一季度，国内在研创新药项目超过1500个，同比增长23%，其中肿瘤领域占比最高，达42%。

二、创新药研发热点
1. 肿瘤免疫治疗：PD-1/PD-L1抑制剂联合治疗策略取得突破，国产药企百济神州、君实生物等在三期临床中展示出与进口药物相当的疗效。双特异性抗体和ADC药物成为新热点，恒瑞医药、信达生物等企业布局积极。

2. 基因治疗：CRISPR基因编辑技术在罕见病治疗领域取得重要进展，国内企业如贝达药业、艾力斯等加速布局。预计未来3-5年将有多个基因治疗产品获批上市。

3. 中枢神经系统疾病：阿尔茨海默症治疗领域出现新突破，绿叶制药、石药集团等企业在研产品进展顺利。

三、政策环境变化
1. 医保政策：集采常态化背景下，创新药医保准入谈判成功率提升，2024年新纳入医保的创新药数量达历史新高，平均降价幅度为43%，低于往年水平。

2. 审批政策：药品优先审评审批通道进一步完善，2024年获批创新药数量同比增长35%，审批周期缩短30%。

3. 知识产权保护：专利链接制度实施细则出台，为创新药企业提供更有力的保护。

四、投资机会分析
1. 创新药龙头：恒瑞医药、百济神州、信达生物等研发管线丰富、商业化能力强的企业有望持续领跑。

2. 细分领域潜力股：肿瘤免疫治疗领域的君实生物、基石药业，基因治疗领域的贝达药业、艾力斯等具备技术壁垒的企业值得关注。

3. 产业链相关：药物研发CRO企业如药明康德、康龙化成，以及创新药生产CDMO企业如凯莱英等有望持续受益于创新药研发浪潮。

五、风险提示
1. 研发失败风险：创新药研发具有高投入、高风险特点，临床试验失败率高。
2. 医保控费风险：医保资金压力加大，创新药准入门槛可能提高。
3. 市场竞争风险：同靶点药物竞争加剧，价格战可能影响盈利能力。
4. 资本市场波动风险：生物医药股票估值波动较大，投资者需关注估值风险。
"""
    industry = "医药"
    
    print(f"分析研报：《{report_title}》")
    print(f"行业：{industry}")
    print("开始分析...")
    
    # 执行分析
    try:
        result = analyzer.analyze_with_five_steps(report_title, report_content, industry)
        
        # 输出结构化结果（不包含完整的分析文本，以避免输出过多）
        print("\n分析结果摘要：")
        summary_result = {
            "analysis": result["analysis"],
        }
        # 移除完整分析文本以简化输出
        if "full_analysis" in summary_result:
            del summary_result["full_analysis"]
            
        print(json.dumps(summary_result, ensure_ascii=False, indent=2))
        
        # 输出一句话总结
        if "summary" in result["analysis"] and "one_line_summary" in result["analysis"]["summary"]:
            print("\n一句话总结：")
            print(result["analysis"]["summary"]["one_line_summary"])
        
        # 输出总分
        if "summary" in result["analysis"] and "completeness_score" in result["analysis"]["summary"]:
            print(f"\n总分：{result['analysis']['summary']['completeness_score']}")
            print(f"评价：{result['analysis']['summary']['evaluation']}")
        
        print("\n测试完成！")
        return True
    except Exception as e:
        print(f"测试过程中出错：{str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main() 