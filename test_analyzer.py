#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试脚本：用于测试 DeepSeekAnalyzer
"""

from deepseek_analyzer import DeepSeekAnalyzer
import json

def main():
    print("开始测试 DeepSeekAnalyzer...")
    
    # 创建分析器实例
    analyzer = DeepSeekAnalyzer()
    
    # 示例研报内容
    report_title = "行业研究报告要点：周度行情回顾与投资建议 (2025年5月11日-5月16日)"
    report_content = """报告要点：
周度行情回顾
2025年5月11日至5月16日，上证综指上涨0.76%，深证成指上涨0.52%，创业板指上涨1.38%。其中申万机械设备上涨0.35%，相较沪深300指数跑输0.76pct，在31个申万一级行业中排名第18。细分子行业来看，申万通用设备/专用设备/轨交设备Ⅱ/工程机械/自动化设备分别涨跌0.96%/1.05%/0.54%/-2.06%/0.44%。
重点板块跟踪
低空经济板块：低空经济领域延续高景气态势，呈现出"事件密集+资本加码+国际联动"的新特征。政策端，四川、重庆加速推进低空经济专项政策，聚焦通用机场、垂直起降场等基建配套，强化财政补贴与场景试点，区域竞争白热化。企业端，亿航、中信海直及海外巨头Archer、Joby密集披露订单与适航进展，eVTOL进入多国协同试飞与商业化落地阶段。国际层面，葡萄牙Airspace World大会推动空域管理系统标准化，巴西、韩国加快AAM产业布局，全球生态链深度整合。技术端，大疆、Dufour等在混动系统、感知技术等核心环节突破，驱动物流、巡检等场景加速应用。
机械设备板块：1.中美双方发布《中美日内瓦经贸会谈联合声明》，本阶段关税谈判落地，后续建议仍密切关注后续中美关税贸易进展。对美出口预计二季度将出现边际提升，同时建议关注具备强海外生产能力及客户多元化的出口链标的。2.工程机械4月整体仍保持较高景气度，内销和出口均保持较强韧性，行业龙头业绩及在手订单均呈现较好增长态势。综上所述，看好工程机械行业二季度景气度持续回暖。
投资建议
低空经济：基建方面，我们建议关注深城交、苏交科、华设集团及纳睿雷达；整机方面，建议关注万丰奥威、亿航智能、纵横股份、绿能慧充；核心零部件方面关注宗申动力、卧龙电驱、应流股份、英搏尔；空管及运营方面关注中信海直、中科星图及四川九洲。
机械设备：出口链板块，我们建议关注巨星科技、泉峰控股、九号公司等；工程机械板块，我们建议关注三一重工、徐工机械、安徽合力等；工业母机板块，我们建议关注华中数控、科德数控、恒立液压等。
风险提示
全球宏观经济增长不及预期风险；企业经营状况低于预期风险；原料价格上升风险；汇率波动风险；竞争格局加剧风险。
"""
    industry = "机械设备"
    
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