import sqlite3
import json
from datetime import datetime
from pathlib import Path
import numpy as np
from typing import List, Dict, Optional, Tuple
from config import Config
import logging
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.db_path = Config.DB_PATH
        self.init_db()
    
    def init_db(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建反思记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reflections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                summary TEXT,
                tags TEXT,
                category TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                type TEXT DEFAULT 'daily',  -- daily, weekly, monthly, yearly, project
                embedding BLOB  -- 存储向量
            )
        ''')
        
        # 创建同步记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                last_sync_at TIMESTAMP,
                sync_status TEXT,
                sync_message TEXT
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON reflections(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_category ON reflections(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_type ON reflections(type)')
        
        conn.commit()
        conn.close()
    
    def add_reflection(self, content: str, summary: str = "", tags: List[str] = None, 
                      category: str = "", type: str = "daily", embedding: np.ndarray = None) -> int:
        """添加新的反思记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        tags_str = json.dumps(tags) if tags else "[]"
        embedding_bytes = embedding.tobytes() if embedding is not None else None
        
        cursor.execute('''
            INSERT INTO reflections (content, summary, tags, category, type, embedding)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (content, summary, tags_str, category, type, embedding_bytes))
        
        reflection_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return reflection_id
    
    def update_reflection(self, id: int, **kwargs):
        """更新反思记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 构建更新语句
        update_fields = []
        values = []
        
        for key, value in kwargs.items():
            if key == 'tags' and isinstance(value, list):
                value = json.dumps(value)
            elif key == 'embedding' and isinstance(value, np.ndarray):
                value = value.tobytes()
            
            update_fields.append(f"{key} = ?")
            values.append(value)
        
        if update_fields:
            values.append(id)
            query = f"UPDATE reflections SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
            cursor.execute(query, values)
            conn.commit()
        
        conn.close()
    
    def get_reflections(self, limit: int = 50, offset: int = 0, 
                       category: str = None, type: str = None) -> List[Dict]:
        """获取反思记录列表"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM reflections WHERE 1=1"
        params = []
        
        if category:
            query += " AND category = ?"
            params.append(category)
        
        if type:
            query += " AND type = ?"
            params.append(type)
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        reflections = []
        for row in rows:
            reflection = dict(row)
            reflection['tags'] = json.loads(reflection['tags']) if reflection['tags'] else []
            # 不返回embedding以节省内存
            reflection.pop('embedding', None)
            reflections.append(reflection)
        
        conn.close()
        return reflections
    
    def search_reflections(self, query: str) -> List[Dict]:
        """关键词搜索反思记录"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM reflections 
            WHERE content LIKE ? OR summary LIKE ? OR tags LIKE ?
            ORDER BY created_at DESC
            LIMIT 50
        ''', (f'%{query}%', f'%{query}%', f'%{query}%'))
        
        rows = cursor.fetchall()
        
        reflections = []
        for row in rows:
            reflection = dict(row)
            reflection['tags'] = json.loads(reflection['tags']) if reflection['tags'] else []
            reflection.pop('embedding', None)
            reflections.append(reflection)
        
        conn.close()
        return reflections
    
    def search_by_embedding(self, query_embedding: np.ndarray, top_k: int = 10) -> List[Tuple[Dict, float]]:
        """向量相似度搜索"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM reflections WHERE embedding IS NOT NULL')
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            reflection = dict(row)
            if reflection['embedding']:
                # 从bytes恢复向量
                db_embedding = np.frombuffer(reflection['embedding'], dtype=np.float32)
                # 计算余弦相似度
                similarity = np.dot(query_embedding, db_embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(db_embedding)
                )
                
                reflection['tags'] = json.loads(reflection['tags']) if reflection['tags'] else []
                reflection.pop('embedding', None)
                results.append((reflection, float(similarity)))
        
        conn.close()
        
        # 按相似度排序并返回top_k
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
    
    def get_categories(self) -> List[str]:
        """获取所有分类"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT DISTINCT category FROM reflections WHERE category != ""')
        categories = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return categories
    
    def get_all_tags(self) -> List[str]:
        """获取所有标签"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT tags FROM reflections')
        all_tags = set()
        
        for row in cursor.fetchall():
            if row[0]:
                tags = json.loads(row[0])
                all_tags.update(tags)
        
        conn.close()
        return list(all_tags)
    
    def delete_reflection(self, id: int):
        """删除反思记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM reflections WHERE id = ?', (id,))
        conn.commit()
        conn.close()
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 总记录数
        cursor.execute('SELECT COUNT(*) FROM reflections')
        total_count = cursor.fetchone()[0]
        
        # 按类型统计
        cursor.execute('SELECT type, COUNT(*) FROM reflections GROUP BY type')
        type_stats = dict(cursor.fetchall())
        
        # 按分类统计
        cursor.execute('SELECT category, COUNT(*) FROM reflections WHERE category != "" GROUP BY category')
        category_stats = dict(cursor.fetchall())
        
        # 最近7天的记录数
        cursor.execute('''
            SELECT COUNT(*) FROM reflections 
            WHERE created_at >= datetime('now', '-7 days')
        ''')
        recent_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_count': total_count,
            'type_stats': type_stats,
            'category_stats': category_stats,
            'recent_count': recent_count
        }
    
    def get_reflections_by_category(self, category):
        """获取特定分类的所有记录"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM reflections 
            WHERE category = ?
            ORDER BY created_at DESC
        ''', (category,))
        
        rows = cursor.fetchall()
        conn.close()
        
        reflections = []
        for row in rows:
            reflection = dict(row)
            # 解析JSON格式的tags
            reflection['tags'] = json.loads(reflection['tags']) if reflection['tags'] else []
            # 不返回embedding以节省内存
            reflection.pop('embedding', None)
            reflections.append(reflection)
        
        return reflections
    
    def get_reflections_by_type(self, type_name):
        """获取特定类型的所有记录"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM reflections 
            WHERE type = ?
            ORDER BY created_at DESC
        ''', (type_name,))
        
        rows = cursor.fetchall()
        conn.close()
        
        reflections = []
        for row in rows:
            reflection = dict(row)
            # 解析JSON格式的tags
            reflection['tags'] = json.loads(reflection['tags']) if reflection['tags'] else []
            # 不返回embedding以节省内存
            reflection.pop('embedding', None)
            reflections.append(reflection)
        
        return reflections
    
    def get_recent_reflections(self, days):
        """获取最近N天的记录"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM reflections 
            WHERE datetime(created_at) >= datetime('now', '-' || ? || ' days')
            ORDER BY created_at DESC
        ''', (days,))
        
        rows = cursor.fetchall()
        conn.close()
        
        reflections = []
        for row in rows:
            reflection = dict(row)
            # 解析JSON格式的tags
            reflection['tags'] = json.loads(reflection['tags']) if reflection['tags'] else []
            # 不返回embedding以节省内存
            reflection.pop('embedding', None)
            reflections.append(reflection)
        
        return reflections 
    

    
    def delete_reflection(self, reflection_id):
        """删除指定的反思记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM reflections WHERE id = ?', (reflection_id,))
            deleted_rows = cursor.rowcount
            conn.commit()
            
            if deleted_rows > 0:
                logger.info(f"删除记录 {reflection_id} 成功")
                return True
            else:
                logger.warning(f"记录 {reflection_id} 不存在")
                return False
                
        except Exception as e:
            logger.error(f"删除记录失败: {e}")
            return False
        finally:
            conn.close()
    
    def get_reflections_by_tag(self, tag):
        """获取包含特定标签的所有记录"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # 使用更可靠的方法搜索标签
            cursor.execute('''
                SELECT * FROM reflections 
                WHERE tags LIKE ?
                ORDER BY created_at DESC
            ''', (f'%"{tag}"%',))
            
            rows = cursor.fetchall()
            conn.close()
            
            reflections = []
            for row in rows:
                reflection = dict(row)
                # 解析JSON格式的tags
                try:
                    reflection['tags'] = json.loads(reflection['tags']) if reflection['tags'] else []
                except (json.JSONDecodeError, TypeError):
                    reflection['tags'] = []
                
                # 再次验证标签是否确实包含目标标签（精确匹配）
                if tag in reflection['tags']:
                    # 不返回embedding以节省内存
                    reflection.pop('embedding', None)
                    reflections.append(reflection)
            
            print(f"[DEBUG] 搜索标签 '{tag}' 找到 {len(reflections)} 条记录")
            return reflections
            
        except Exception as e:
            print(f"[DEBUG] 标签搜索出错: {e}")
            logger.error(f"标签搜索失败: {e}")
            conn.close()
            return [] 
    
    def get_all_reflection_ids(self):
        """获取所有记录的ID列表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM reflections')
        ids = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return ids 