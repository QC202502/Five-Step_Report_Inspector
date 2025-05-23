#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试脚本：用于测试 DeepSeekAnalyzer 分析新的研报
"""

from deepseek_analyzer import DeepSeekAnalyzer
import json

def main():
    print("开始测试 DeepSeekAnalyzer 分析新研报...")
    
    # 创建分析器实例
    analyzer = DeepSeekAnalyzer()
    
    # 新的研报内容
    report_title = "电子行业周报：AI PC需求强劲，半导体设备国产化加速"
    report_content = """
摘要：
本周电子板块整体表现平稳，AI PC需求持续增长，NVIDIA与联发科合作推进AI PC发展。半导体设备国产化进程加速，中微公司新型刻蚀设备获突破。消费电子方面，智能手表市场份额重新洗牌，国产品牌增长显著。

市场表现：
本周（2025年6月1日-6月7日）上证指数上涨1.2%，深证成指上涨0.8%，创业板指上涨1.5%。电子行业指数上涨1.7%，跑赢大盘0.5个百分点。细分领域中，半导体设备板块表现最佳，上涨3.2%；消费电子板块上涨1.5%；面板显示板块上涨0.9%。

行业动态：
1. AI PC市场：据IDC最新数据，预计2025年AI PC出货量将达8500万台，同比增长45%。NVIDIA宣布与联发科合作开发新一代AI PC芯片组，预计将于2026年初量产。戴尔、惠普等厂商已发布多款搭载AI芯片的新品，出货情况良好。

2. 半导体设备：中微公司宣布其12nm制程刻蚀设备已通过客户验证，国产替代进程加速。国内晶圆厂扩产需求旺盛，设备订单充足。全球半导体设备销售额预计2025年将达1100亿美元，同比增长12%。

3. 消费电子：全球智能手表市场份额变动明显，苹果市占率下滑至34%，华为增长至15%，小米达到11%。国内智能手机市场5月出货量同比增长5%，高端机型占比提升。

投资建议：
1. 重点关注AI PC产业链，包括GPU/NPU芯片设计、存储芯片、高速接口等细分领域，推荐关注：寒武纪、澜起科技、兆易创新。

2. 半导体设备国产化进程加速，设备厂商订单饱满，建议关注：中微公司、北方华创、盛美上海。

3. 消费电子板块中，智能穿戴设备增长确定性高，建议关注：立讯精密、歌尔股份、闻泰科技。

风险提示：
1. 全球经济增速放缓风险
2. 行业竞争加剧风险
3. 技术迭代不及预期风险
4. 产能扩张过快导致供过于求风险
"""
    industry = "电子"
    
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