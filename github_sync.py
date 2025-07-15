import os
import json
import sqlite3
from datetime import datetime
from pathlib import Path
import base64
from github import Github, GithubException
from config import Config
import logging

logger = logging.getLogger(__name__)

class GitHubSync:
    def __init__(self):
        self.token = Config.GITHUB_TOKEN
        self.repo_name = Config.GITHUB_REPO
        self.branch = Config.GITHUB_BRANCH
        self.github = None
        self.repo = None
        
        if self.token and self.repo_name:
            try:
                self.github = Github(self.token)
                self.repo = self.github.get_repo(self.repo_name)
                logger.info(f"GitHub连接成功: {self.repo_name}")
            except Exception as e:
                logger.error(f"GitHub连接失败: {e}")
    
    def is_configured(self) -> bool:
        """检查是否配置了GitHub同步"""
        return bool(self.token and self.repo_name and self.repo)
    
    def export_to_json(self, db_path: Path) -> str:
        """将数据库导出为JSON格式"""
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 导出所有反思记录
        cursor.execute('SELECT * FROM reflections ORDER BY created_at')
        reflections = []
        
        for row in cursor.fetchall():
            reflection = dict(row)
            # 处理JSON字段
            if reflection['tags']:
                reflection['tags'] = json.loads(reflection['tags'])
            # 不导出embedding以减小文件大小
            reflection.pop('embedding', None)
            reflections.append(reflection)
        
        # 导出统计信息
        cursor.execute('SELECT COUNT(*) FROM reflections')
        total_count = cursor.fetchone()[0]
        
        export_data = {
            'export_time': datetime.now().isoformat(),
            'total_count': total_count,
            'reflections': reflections
        }
        
        conn.close()
        return json.dumps(export_data, ensure_ascii=False, indent=2)
    
    def sync_to_github(self, db_path: Path) -> bool:
        """同步数据到GitHub"""
        if not self.is_configured():
            logger.warning("GitHub未配置，跳过同步")
            return False
        
        try:
            # 导出数据
            json_content = self.export_to_json(db_path)
            file_path = f"reflections_backup_{datetime.now().strftime('%Y%m')}.json"
            
            # 检查文件是否存在
            try:
                file = self.repo.get_contents(file_path, ref=self.branch)
                # 更新文件
                self.repo.update_file(
                    path=file_path,
                    message=f"Update reflections backup - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    content=json_content,
                    sha=file.sha,
                    branch=self.branch
                )
                logger.info(f"更新GitHub文件成功: {file_path}")
            except GithubException:
                # 创建新文件
                self.repo.create_file(
                    path=file_path,
                    message=f"Create reflections backup - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    content=json_content,
                    branch=self.branch
                )
                logger.info(f"创建GitHub文件成功: {file_path}")
            
            # 更新同步日志
            self._update_sync_log(db_path, "success", "同步成功")
            return True
            
        except Exception as e:
            logger.error(f"GitHub同步失败: {e}")
            self._update_sync_log(db_path, "error", str(e))
            return False
    
    def sync_from_github(self, db_path: Path) -> bool:
        """从GitHub同步数据"""
        if not self.is_configured():
            logger.warning("GitHub未配置，跳过同步")
            return False
        
        try:
            # 获取最新的备份文件
            contents = self.repo.get_contents("", ref=self.branch)
            backup_files = [f for f in contents if f.name.startswith("reflections_backup_") and f.name.endswith(".json")]
            
            if not backup_files:
                logger.info("GitHub上没有备份文件")
                return False
            
            # 按文件名排序，获取最新的
            backup_files.sort(key=lambda x: x.name, reverse=True)
            latest_file = backup_files[0]
            
            # 下载文件内容
            file_content = base64.b64decode(latest_file.content).decode('utf-8')
            data = json.loads(file_content)
            
            # 导入数据到本地数据库
            return self._import_from_json(db_path, data)
            
        except Exception as e:
            logger.error(f"从GitHub同步失败: {e}")
            return False
    
    def _import_from_json(self, db_path: Path, data: dict) -> bool:
        """从JSON数据导入到数据库"""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 清空现有数据（可选，或者实现合并逻辑）
            cursor.execute('DELETE FROM reflections')
            
            # 导入数据
            for reflection in data['reflections']:
                tags_str = json.dumps(reflection['tags'], ensure_ascii=False) if reflection['tags'] else "[]"
                
                cursor.execute('''
                    INSERT INTO reflections (id, content, summary, tags, category, created_at, updated_at, type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    reflection['id'],
                    reflection['content'],
                    reflection.get('summary', ''),
                    tags_str,
                    reflection.get('category', ''),
                    reflection['created_at'],
                    reflection['updated_at'],
                    reflection.get('type', 'daily')
                ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"成功导入 {len(data['reflections'])} 条记录")
            return True
            
        except Exception as e:
            logger.error(f"导入数据失败: {e}")
            return False
    
    def _update_sync_log(self, db_path: Path, status: str, message: str):
        """更新同步日志"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO sync_log (last_sync_at, sync_status, sync_message)
            VALUES (?, ?, ?)
        ''', (datetime.now(), status, message))
        
        conn.commit()
        conn.close()
    
    def get_last_sync_info(self, db_path: Path) -> dict:
        """获取最后同步信息"""
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM sync_log 
            ORDER BY last_sync_at DESC 
            LIMIT 1
        ''')
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None 