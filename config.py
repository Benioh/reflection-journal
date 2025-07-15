import os
from pathlib import Path
from dotenv import load_dotenv

# 只在.env文件存在时加载
env_path = Path('.env')
if env_path.exists():
    load_dotenv()

class Config:
    """
    应用配置 - 智能默认值，可选配置
    
    使用优先级：
    1. 环境变量（.env文件）
    2. 默认值（无需配置即可使用）
    """
    
    # 核心配置 - 这些都有合理的默认值
    APP_DATA_DIR = Path(os.getenv('APP_DATA_DIR', './data'))
    DB_PATH = APP_DATA_DIR / 'reflections.db'
    
    # AI配置 - 可选，不配置也能用
    DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
    DEEPSEEK_API_BASE = 'https://api.deepseek.com'  # 固定值，无需配置
    
    # GitHub同步 - 可选功能
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')
    GITHUB_REPO = os.getenv('GITHUB_REPO', '')
    GITHUB_BRANCH = 'main'  # 固定默认值
    
    # 模型配置 - 自动选择最佳方案
    USE_QWEN_MODEL = os.getenv('USE_QWEN_MODEL', 'auto')  # auto/true/false
    
    # 模型下载源 - 支持 huggingface 或 modelscope
    MODEL_SOURCE = os.getenv('MODEL_SOURCE', 'modelscope')  # 默认使用ModelScope（国内快）
    
    # 智能模型选择
    if USE_QWEN_MODEL == 'auto':
        # 自动检测：如果已安装Qwen模型则使用，否则使用轻量级模型
        try:
            import torch
            # 有GPU或内存>8GB时使用Qwen
            has_gpu = torch.cuda.is_available()
            import psutil
            has_enough_ram = psutil.virtual_memory().total > 8 * 1024 * 1024 * 1024
            USE_QWEN_MODEL = 'true' if (has_gpu or has_enough_ram) else 'false'
        except:
            USE_QWEN_MODEL = 'false'
    
    # 根据选择设置模型
    if USE_QWEN_MODEL == 'true':
        if MODEL_SOURCE == 'modelscope':
            # ModelScope模型ID
            EMBEDDING_MODEL = 'Qwen/Qwen3-Embedding-0.6B'
            MODEL_CACHE_DIR = APP_DATA_DIR / 'models' / 'modelscope'
        else:
            # HuggingFace模型ID
            EMBEDDING_MODEL = 'Qwen/Qwen3-Embedding-0.6B'
            MODEL_CACHE_DIR = APP_DATA_DIR / 'models' / 'huggingface'
    else:
        EMBEDDING_MODEL = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
        MODEL_CACHE_DIR = APP_DATA_DIR / 'models' / 'sentence_transformers'
    
    # 确保缓存目录存在
    MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    # UI配置 - 固定值
    WINDOW_WIDTH = 1200
    WINDOW_HEIGHT = 800
    THEME_MODE = "light"
    
    # 确保数据目录存在
    APP_DATA_DIR.mkdir(exist_ok=True)
    
    @classmethod
    def get_config_summary(cls):
        """获取配置摘要"""
        summary = []
        if cls.DEEPSEEK_API_KEY:
            summary.append("✓ AI分析已启用")
        else:
            summary.append("○ AI分析未配置（使用本地分析）")
            
        if cls.GITHUB_TOKEN and cls.GITHUB_REPO:
            summary.append("✓ GitHub同步已启用")
        else:
            summary.append("○ GitHub同步未配置（仅本地存储）")
            
        model_info = f"✓ 使用模型: {'Qwen3' if 'Qwen' in cls.EMBEDDING_MODEL else '轻量级模型'}"
        if 'Qwen' in cls.EMBEDDING_MODEL:
            model_info += f" (源: {cls.MODEL_SOURCE})"
        summary.append(model_info)
        
        return summary
    
    @classmethod
    def create_minimal_env(cls):
        """创建最小化的.env示例"""
        minimal_env = """# 复盘日志配置文件（可选）
# 不配置也可以正常使用，以下是可选的增强功能

# AI分析功能（可选）
# 获取密钥: https://platform.deepseek.com/
DEEPSEEK_API_KEY=

# GitHub同步（可选）
# 用于多设备同步数据
GITHUB_TOKEN=
GITHUB_REPO=

# 模型设置（可选）
# USE_QWEN_MODEL=true  # 使用Qwen模型（auto/true/false）
# MODEL_SOURCE=modelscope  # 模型下载源（modelscope/huggingface）
"""
        with open('.env.example', 'w', encoding='utf-8') as f:
            f.write(minimal_env) 