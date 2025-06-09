#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
禁用DeepSeek API自动调用脚本
此脚本通过修改环境变量和创建禁用标志来停止DeepSeek API的自动调用，但不删除任何代码
"""

import os
import sys
import logging
from datetime import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('deepseek_disable.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def create_disable_flag():
    """创建禁用标志文件"""
    try:
        with open('.deepseek_disabled', 'w') as f:
            f.write(f"禁用时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("已创建DeepSeek API禁用标志文件")
        return True
    except Exception as e:
        logger.error(f"创建禁用标志文件失败: {e}")
        return False

def create_or_update_env_file():
    """创建或更新.env文件，禁用DeepSeek API"""
    try:
        # 如果.env文件不存在，就从.env.example复制
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        env_example_path = os.path.join(os.path.dirname(__file__), '.env.example')
        
        if not os.path.exists(env_path) and os.path.exists(env_example_path):
            logger.info("从.env.example创建.env文件")
            with open(env_example_path, 'r', encoding='utf-8') as src:
                content = src.read()
            
            # 替换DeepSeek API密钥
            content = content.replace('DEEPSEEK_API_KEY=your_deepseek_api_key_here', 
                                     'DEEPSEEK_API_KEY=DISABLED_INTENTIONALLY')
            
            with open(env_path, 'w', encoding='utf-8') as dest:
                dest.write(content)
            
            logger.info("已从.env.example创建.env文件并禁用DeepSeek API")
            return True
            
        # 如果.env文件存在，则更新它
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 查找并替换DeepSeek API密钥行
            api_key_found = False
            new_lines = []
            for line in lines:
                if line.startswith('DEEPSEEK_API_KEY='):
                    new_lines.append('DEEPSEEK_API_KEY=DISABLED_INTENTIONALLY\n')
                    api_key_found = True
                    logger.info("已禁用.env文件中的DeepSeek API密钥")
                else:
                    new_lines.append(line)
            
            # 如果没有找到API密钥行，则添加一行
            if not api_key_found:
                new_lines.append('\n# DeepSeek API已被禁用\n')
                new_lines.append('DEEPSEEK_API_KEY=DISABLED_INTENTIONALLY\n')
                logger.info("已添加禁用的DeepSeek API密钥行")
            
            with open(env_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            
            logger.info("已更新.env文件")
            return True
        else:
            # 如果.env文件和.env.example都不存在，则创建新的.env文件
            logger.info(".env文件不存在，创建新文件")
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write('# 五步法研报分析器环境变量配置\n')
                f.write('# DeepSeek API已被禁用\n')
                f.write('DEEPSEEK_API_KEY=DISABLED_INTENTIONALLY\n')
                f.write('DEEPSEEK_API_URL=https://api.deepseek.com/v1/chat/completions\n')
                f.write('DEEPSEEK_MODEL=deepseek-chat\n')
            
            logger.info("已创建.env文件并禁用DeepSeek API")
            return True
    except Exception as e:
        logger.error(f"更新.env文件失败: {e}")
        return False

def patch_deepseek_analyzer():
    """修改deepseek_analyzer.py文件，添加禁用检查"""
    try:
        file_path = os.path.join(os.path.dirname(__file__), 'deepseek_analyzer.py')
        if not os.path.exists(file_path):
            logger.error("找不到deepseek_analyzer.py文件")
            return False
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 检查是否已经添加了禁用检查
        if '.deepseek_disabled' in content:
            logger.info("deepseek_analyzer.py已包含禁用检查，无需修改")
            return True
            
        # 查找_ask_deepseek方法的开始位置
        method_start = content.find('def _ask_deepseek')
        if method_start == -1:
            logger.error("在deepseek_analyzer.py中找不到_ask_deepseek方法")
            return False
            
        # 在方法中添加禁用检查代码
        indent = ' ' * 8  # 假设缩进是8个空格
        disable_check = f'''
{indent}# 检查是否禁用了DeepSeek API
{indent}if os.path.exists('.deepseek_disabled'):
{indent}    print("警告: DeepSeek API已被禁用，请删除.deepseek_disabled文件以重新启用。")
{indent}    return (
{indent}        "## 体检清单\\n| 五步要素 | 是否覆盖 | 快评 |\\n| --- | --- | --- |\\n"
{indent}        "| 信息 | ❌ | DeepSeek API已被禁用 |\\n"
{indent}        "## 五步框架梳理\\n| 步骤 | 核心内容提炼 |\\n| --- | --- |\\n"
{indent}        "| Information | [DeepSeek API已被禁用] |\\n"
{indent}        "## 一句话总结\\n[DeepSeek API已被禁用，无法生成分析]\\n"
{indent}    )
'''
        
        # 在方法开始位置后添加禁用检查
        method_body_start = content.find(':', method_start)
        if method_body_start == -1:
            logger.error("无法定位_ask_deepseek方法体")
            return False
            
        # 找到方法体第一行的位置
        next_line_start = content.find('\n', method_body_start) + 1
        if next_line_start <= 0:
            logger.error("无法定位_ask_deepseek方法体的第一行")
            return False
            
        # 修改内容
        new_content = content[:next_line_start] + disable_check + content[next_line_start:]
        
        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        logger.info("已成功在deepseek_analyzer.py中添加禁用检查")
        return True
    except Exception as e:
        logger.error(f"修改deepseek_analyzer.py失败: {e}")
        return False

def main():
    """主函数"""
    logger.info("开始执行禁用DeepSeek API自动调用脚本")
    
    # 创建禁用标志
    flag_created = create_disable_flag()
    
    # 更新环境变量文件
    env_updated = create_or_update_env_file()
    
    # 修改deepseek_analyzer.py
    code_patched = patch_deepseek_analyzer()
    
    if flag_created and env_updated and code_patched:
        logger.info("DeepSeek API自动调用已成功禁用")
        logger.info("重要: 如果要恢复使用，请编辑.env文件设置有效的API密钥，并删除.deepseek_disabled文件")
        print("\n===========================================================")
        print("成功禁用DeepSeek API的自动调用！")
        print("操作完成：")
        print("1. 创建了禁用标志文件 .deepseek_disabled")
        print("2. 修改了环境变量，将API密钥替换为DISABLED_INTENTIONALLY")
        print("3. 在deepseek_analyzer.py中添加了禁用检查逻辑")
        print("\n要恢复API调用功能，请：")
        print("1. 删除 .deepseek_disabled 文件")
        print("2. 编辑 .env 文件，设置有效的API密钥")
        print("===========================================================\n")
        return True
    else:
        warning_msg = "禁用DeepSeek API过程中出现一些问题，请检查日志"
        logger.warning(warning_msg)
        print(f"\n警告: {warning_msg}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 