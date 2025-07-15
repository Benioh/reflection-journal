#!/usr/bin/env python
"""
改进版打包脚本 - 支持即开即用
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path
import zipfile

def create_launcher():
    """创建启动器，处理首次运行配置"""
    launcher_code = '''import os
import sys
from pathlib import Path

def first_run_setup():
    """首次运行设置向导"""
    config_path = Path(".env")
    
    if not config_path.exists():
        print("=== 欢迎使用复盘日志 ===\\n")
        print("检测到首次运行，让我们进行快速配置：\\n")
        
        # 基础配置
        use_ai = input("是否使用AI分析功能？(y/n，默认n): ").lower() == 'y'
        use_sync = input("是否使用GitHub同步功能？(y/n，默认n): ").lower() == 'y'
        
        config_lines = []
        
        if use_ai:
            print("\\n请访问 https://platform.deepseek.com/ 获取API密钥")
            api_key = input("请输入DeepSeek API密钥（可以稍后配置）: ").strip()
            config_lines.append(f"DEEPSEEK_API_KEY={api_key}")
            config_lines.append("DEEPSEEK_API_BASE=https://api.deepseek.com")
        else:
            config_lines.append("DEEPSEEK_API_KEY=")
            
        if use_sync:
            print("\\n配置GitHub同步：")
            print("1. 在GitHub创建私有仓库")
            print("2. 获取Personal Access Token")
            token = input("请输入GitHub Token（可以稍后配置）: ").strip()
            repo = input("请输入仓库名（格式: 用户名/仓库名）: ").strip()
            config_lines.append(f"GITHUB_TOKEN={token}")
            config_lines.append(f"GITHUB_REPO={repo}")
            config_lines.append("GITHUB_BRANCH=main")
        else:
            config_lines.append("GITHUB_TOKEN=")
            config_lines.append("GITHUB_REPO=")
            
        # 模型配置
        print("\\n选择嵌入模型：")
        print("1. Qwen3 0.6B（推荐，约1.2GB，首次运行需下载）")
        print("2. 轻量级模型（约400MB）")
        model_choice = input("请选择 (1/2，默认2): ").strip()
        
        if model_choice == "1":
            config_lines.append("USE_QWEN_MODEL=true")
            config_lines.append("QWEN_MODEL_SIZE=0.6B")
        else:
            config_lines.append("USE_QWEN_MODEL=false")
            
        config_lines.append("EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        config_lines.append("APP_DATA_DIR=./data")
        
        # 写入配置
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write('\\n'.join(config_lines))
            
        print("\\n配置完成！应用即将启动...")
        print("提示：你可以随时编辑 .env 文件修改配置")
        input("\\n按回车键继续...")

# 首次运行检查
first_run_setup()

# 导入并运行主程序
from main import ReflectionJournalApp
import flet as ft

if __name__ == "__main__":
    app = ReflectionJournalApp()
    ft.app(target=app.main)
'''
    
    with open("launcher.py", "w", encoding="utf-8") as f:
        f.write(launcher_code)

# 已删除 create_portable_config 函数，不再需要

def build_app_improved(platform):
    """改进版构建"""
    
    # 检查依赖
    try:
        import flet
    except ImportError:
        print("请先安装依赖: pip install -r requirements.txt")
        sys.exit(1)
    
    # 清理
    for path in ["dist", "build", "launcher.py", "portable_config.env"]:
        if Path(path).exists():
            if Path(path).is_dir():
                shutil.rmtree(path)
            else:
                os.remove(path)
    
    # 创建启动器
    print("创建启动器...")
    create_launcher()
    
    # 便携版配置已不再需要
    
    app_name = "ReflectionJournal"
    
    # 构建命令 - 使用launcher.py作为入口
    base_cmd = [
        "flet", "pack", "launcher.py",
        "--name", app_name,
        "--product-name", "复盘日志",
        "--product-version", "1.0.0",
        "--copyright", "Copyright (c) 2024",
    ]
    
    # 添加数据文件
    data_files = [
                    "--add-data", "env_example:.",
        # 包含所有Python模块
        "--add-data", "main.py:.",
        "--add-data", "database.py:.",
        "--add-data", "ai_service.py:.",
        "--add-data", "github_sync.py:.",
        "--add-data", "sync_manager.py:.",
        "--add-data", "config.py:.",
    ]
    
    # 平台特定配置
    if platform == "windows":
        if Path("icon.ico").exists():
            base_cmd.extend(["--icon", "icon.ico"])
        # Windows需要隐藏控制台
        base_cmd.extend(["--noconsole"])
    elif platform == "macos":
        if Path("icon.icns").exists():
            base_cmd.extend(["--icon", "icon.icns"])
    elif platform == "linux":
        if Path("icon.png").exists():
            base_cmd.extend(["--icon", "icon.png"])
    
    # 组合命令
    cmd = base_cmd + data_files
    
    print(f"开始构建 {platform} 应用...")
    
    try:
        subprocess.run(cmd, check=True)
        print(f"\n构建成功！")
        
        # 创建发布包
        dist_dir = Path("dist")
        
        if platform == "windows":
            # Windows - 创建便携版文件夹
            portable_dir = dist_dir / "ReflectionJournal-Portable"
            portable_dir.mkdir(exist_ok=True)
            
            # 复制文件
            shutil.copy(dist_dir / f"{app_name}.exe", portable_dir)
            # 复制配置示例文件
            if Path("env_example").exists():
                shutil.copy("env_example", portable_dir / "env_example")
            
            # 创建启动说明
            with open(portable_dir / "使用说明.txt", "w", encoding="utf-8") as f:
                f.write("复盘日志 - 便携版\n\n")
                f.write("1. 双击 ReflectionJournal.exe 启动\n")
                f.write("2. 首次运行会引导你进行配置\n")
                f.write("3. 所有数据保存在 data 文件夹\n")
                f.write("4. 可以将整个文件夹复制到U盘随身携带\n")
            
            # 创建ZIP包
            zip_name = f"ReflectionJournal-{platform}-portable.zip"
            with zipfile.ZipFile(dist_dir / zip_name, 'w') as zf:
                for file in portable_dir.rglob('*'):
                    zf.write(file, file.relative_to(portable_dir))
            
            print(f"\n便携版创建成功: dist/{zip_name}")
            
        elif platform == "macos":
            # macOS - 创建DMG（需要额外工具）
            print("\nmacOS应用创建成功: dist/ReflectionJournal.app")
            print("提示：可以使用 create-dmg 工具创建DMG安装包")
        
        # 清理临时文件
        for temp_file in ["launcher.py"]:
            if Path(temp_file).exists():
                os.remove(temp_file)
                
    except subprocess.CalledProcessError as e:
        print(f"构建失败: {e}")
        sys.exit(1)

def create_icon():
    """创建默认图标"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        size = 512
        img = Image.new('RGBA', (size, size), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        
        # 渐变背景
        for i in range(size):
            color = int(66 + (133 - 66) * i / size)
            draw.rectangle([0, i, size, i+1], fill=(66, color, 244, 255))
        
        # 圆形遮罩
        mask = Image.new('L', (size, size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse([0, 0, size, size], fill=255)
        img.putalpha(mask)
        
        # 文字
        text = "记"
        try:
            # 尝试使用中文字体
            font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", int(size * 0.4))
        except:
            font = ImageFont.load_default()
        
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (size - text_width) // 2
        y = (size - text_height) // 2 - bbox[1]
        draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)
        
        # 保存
        img.save("icon.png")
        img.save("icon.ico", format='ICO', sizes=[(256, 256)])
        
        print("已创建默认图标")
        
    except ImportError:
        print("提示: 安装Pillow可以生成更好的图标")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("使用方法: python build_improved.py [windows|macos|linux]")
        sys.exit(1)
    
    platform = sys.argv[1].lower()
    
    # 创建图标
    if not any(Path(f"icon.{ext}").exists() for ext in ["png", "ico", "icns"]):
        create_icon()
    
    # 构建应用
    build_app_improved(platform) 