import requests
import json
from typing import List, Dict, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
from config import Config
import logging
import torch
import os
import sys

logger = logging.getLogger(__name__)

# 尝试导入modelscope
try:
    from modelscope import snapshot_download
    HAS_MODELSCOPE = True
    logger.info("ModelScope已安装，可以使用国内镜像加速下载")
except ImportError:
    HAS_MODELSCOPE = False
    logger.info("ModelScope未安装，将使用HuggingFace下载")

class AIService:
    def __init__(self):
        self.api_key = Config.DEEPSEEK_API_KEY
        self.api_base = Config.DEEPSEEK_API_BASE
        
        # 初始化嵌入模型
        self._init_embedding_model()
    
    def _init_embedding_model(self):
        """初始化嵌入模型"""
        try:
            # 使用配置中智能选择的模型
            model_name = Config.EMBEDDING_MODEL
            logger.info(f"正在加载嵌入模型: {model_name}")
            
            # 检查设备
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"使用设备: {device}")
            
            # 根据模型源加载模型
            if "Qwen" in model_name and Config.MODEL_SOURCE == 'modelscope' and HAS_MODELSCOPE:
                # 使用ModelScope下载Qwen模型
                logger.info("使用ModelScope下载模型（国内速度更快）...")
                self.embedding_model = self._load_from_modelscope(model_name, device)
            else:
                # 使用HuggingFace或直接加载
                if "Qwen" in model_name:
                    if Config.MODEL_SOURCE == 'modelscope' and not HAS_MODELSCOPE:
                        logger.warning("配置使用ModelScope但未安装，将使用HuggingFace下载")
                        logger.info("提示：运行 pip install modelscope 可启用国内加速")
                    logger.info("使用HuggingFace下载模型...")
                    self.embedding_model = SentenceTransformer(
                        model_name,
                        device=device,
                        trust_remote_code=True,
                        cache_folder=str(Config.MODEL_CACHE_DIR)
                    )
                else:
                    self.embedding_model = SentenceTransformer(
                        model_name,
                        device=device,
                        cache_folder=str(Config.MODEL_CACHE_DIR)
                    )
            
            # 设置为评估模式
            self.embedding_model.eval()
            logger.info(f"嵌入模型加载成功")
            
        except Exception as e:
            logger.error(f"加载嵌入模型失败: {e}")
            logger.info("将使用备用的轻量级模型")
            try:
                # 强制使用轻量级模型作为备用
                fallback_model = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
                self.embedding_model = SentenceTransformer(
                    fallback_model,
                    cache_folder=str(Config.MODEL_CACHE_DIR)
                )
                logger.info(f"备用模型加载成功")
            except:
                self.embedding_model = None
                logger.error("所有嵌入模型加载失败，向量搜索功能将不可用")
    
    def _load_from_modelscope(self, model_name: str, device: str):
        """从ModelScope加载模型"""
        try:
            # ModelScope上的模型ID
            modelscope_model_id = model_name
            if model_name == "Qwen/Qwen3-Embedding-0.6B":
                # ModelScope上使用小写
                modelscope_model_id = "qwen/Qwen3-Embedding-0.6B"
            
            logger.info(f"从ModelScope下载: {modelscope_model_id}")
            
            # 下载模型到缓存目录
            model_dir = snapshot_download(
                modelscope_model_id,
                cache_dir=str(Config.MODEL_CACHE_DIR),
                revision='master'
            )
            
            logger.info(f"ModelScope模型下载完成: {model_dir}")
            
            # 使用下载的模型路径加载
            return SentenceTransformer(
                model_dir,
                device=device,
                trust_remote_code=True
            )
            
        except Exception as e:
            logger.error(f"从ModelScope加载失败: {e}")
            logger.info("尝试使用HuggingFace...")
            # 回退到HuggingFace
            return SentenceTransformer(
                model_name,
                device=device,
                trust_remote_code=True,
                cache_folder=str(Config.MODEL_CACHE_DIR)
            )
    
    def analyze_content(self, content: str) -> Dict:
        """使用DeepSeek API分析内容，生成摘要、标签和分类"""
        if not self.api_key:
            logger.info("DeepSeek API未配置，使用本地分析")
            return self._fallback_analysis(content)
        
        prompt = f"""请分析以下内容，并返回JSON格式的结果：

内容：
{content}

请返回以下信息：
1. summary: 一句话总结（不超过50字）
2. tags: 相关标签列表（3-5个）
3. category: 内容分类（技术/生活/学习/工作/思考/其他）

返回格式：
{{
    "summary": "内容的一句话总结",
    "tags": ["标签1", "标签2", "标签3"],
    "category": "分类"
}}"""

        try:
            response = requests.post(
                f"{self.api_base}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": "你是一个专业的内容分析助手，擅长提取关键信息。请用中文回复。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 500,
                    "response_format": {"type": "json_object"}
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content_text = result['choices'][0]['message']['content']
                
                try:
                    analysis = json.loads(content_text)
                    return {
                        'summary': analysis.get('summary', ''),
                        'tags': analysis.get('tags', []),
                        'category': analysis.get('category', '其他')
                    }
                except json.JSONDecodeError:
                    logger.error("解析AI响应失败")
                    return self._fallback_analysis(content)
            else:
                logger.error(f"DeepSeek API调用失败: {response.status_code}")
                return self._fallback_analysis(content)
                
        except Exception as e:
            logger.error(f"AI分析出错: {e}")
            return self._fallback_analysis(content)
    
    def _fallback_analysis(self, content: str) -> Dict:
        """备用分析方法 - 改进版"""
        # 提取关键词
        keywords = []
        
        # 分类关键词映射
        category_keywords = {
            '技术': ['代码', '编程', '开发', '技术', 'API', '数据库', '算法', '框架', '语言', '工具', 
                    'bug', '调试', '性能', '架构', '设计模式', '测试', '部署'],
            '生活': ['生活', '日常', '感悟', '心情', '记录', '感受', '体验', '家人', '朋友', 
                    '健康', '运动', '旅行', '美食', '休息'],
            '学习': ['学习', '知识', '理解', '掌握', '练习', '课程', '书籍', '阅读', '笔记', 
                    '总结', '复习', '考试', '进步'],
            '工作': ['工作', '项目', '任务', '会议', '汇报', '进度', '计划', '团队', '同事', 
                    '客户', '需求', '交付', '反馈'],
            '思考': ['思考', '想法', '观点', '理念', '反思', '总结', '复盘', '规划', '目标', 
                    '价值', '意义', '选择', '决定']
        }
        
        # 统计各类别的匹配数
        category_scores = {}
        for category, kw_list in category_keywords.items():
            score = sum(1 for kw in kw_list if kw in content)
            if score > 0:
                category_scores[category] = score
                # 收集匹配到的关键词
                keywords.extend([kw for kw in kw_list if kw in content])
        
        # 选择得分最高的类别
        if category_scores:
            category = max(category_scores, key=category_scores.get)
        else:
            category = '其他'
        
        # 去重并限制标签数量
        keywords = list(set(keywords))[:5]
        
        # 生成摘要 - 提取第一句完整的话
        sentences = content.replace('。', '。\n').replace('！', '！\n').replace('？', '？\n').split('\n')
        first_sentence = next((s.strip() for s in sentences if s.strip()), content[:50])
        summary = first_sentence[:50] + '...' if len(first_sentence) > 50 else first_sentence
        
        return {
            'summary': summary,
            'tags': keywords[:3] if keywords else [category, '记录'],
            'category': category
        }
    
    def generate_embedding(self, text: str) -> np.ndarray:
        """生成文本向量"""
        if self.embedding_model is None:
            return None
        
        try:
            with torch.no_grad():
                embedding = self.embedding_model.encode(
                    text, 
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                    show_progress_bar=False
                )
            return embedding.astype(np.float32)
        except Exception as e:
            logger.error(f"生成向量失败: {e}")
            return None
    
    def find_similar_ideas(self, query: str, embeddings: List[Tuple[int, np.ndarray]], top_k: int = 5) -> List[Tuple[int, float]]:
        """查找相似的想法"""
        if self.embedding_model is None:
            return []
        
        try:
            with torch.no_grad():
                query_embedding = self.embedding_model.encode(
                    query,
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                    show_progress_bar=False
                )
            
            if query_embedding is None:
                return []
            
            similarities = []
            for id, embedding in embeddings:
                # 计算余弦相似度
                similarity = np.dot(query_embedding, embedding)
                similarities.append((id, float(similarity)))
            
            # 按相似度排序
            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:top_k]
            
        except Exception as e:
            logger.error(f"查找相似想法失败: {e}")
            return [] 