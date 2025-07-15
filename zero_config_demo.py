#!/usr/bin/env python
"""
零配置运行演示 - 展示无需任何配置即可使用
"""
import os
from pathlib import Path

# 确保没有配置文件
if Path('.env').exists():
    print("检测到.env文件，重命名为.env.backup")
    os.rename('.env', '.env.backup')

print("=== 零配置运行演示 ===\n")
print("正在启动应用，无需任何配置...")
print("功能说明：")
print("✓ 本地记录和存储")
print("✓ 关键词搜索") 
print("✓ 基础AI分析（本地）")
print("✓ 轻量级向量搜索")
print("✗ DeepSeek AI分析（需要API密钥）")
print("✗ GitHub同步（需要配置）")
print("\n启动中...\n")

# 导入并运行主程序
from main import ReflectionJournalApp
import flet as ft

if __name__ == "__main__":
    app = ReflectionJournalApp()
    
    # 显示配置信息
    from config import Config
    print("当前配置：")
    for line in Config.get_config_summary():
        print(f"  {line}")
    print()
    
    ft.app(target=app.main) 