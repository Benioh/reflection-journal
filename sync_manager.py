import os
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
import threading
import time
from typing import Dict, List, Tuple, Optional
import hashlib
from config import Config
from github_sync import GitHubSync
import logging

logger = logging.getLogger(__name__)

class SyncManager:
    """管理自动同步和冲突解决"""
    
    def __init__(self, db_path: Path, sync_deletions: bool = True):
        self.db_path = db_path
        self.github_sync = GitHubSync()
        self.sync_interval = 30  # 30秒自动同步一次
        self.sync_thread = None
        self.is_syncing = False
        self.sync_callbacks = []  # 同步完成后的回调函数
        self.sync_deletions = sync_deletions  # 是否同步删除操作（默认启用）
        
        # 同步状态文件路径
        self.sync_state_file = self.db_path.parent / '.sync_state.json'
        
        # 加载上次同步时间
        self.last_sync_time = self._load_last_sync_time()
        
    def start_auto_sync(self):
        """启动自动同步"""
        if not self.github_sync.is_configured():
            logger.info("GitHub未配置，跳过自动同步")
            return
            
        # 启动时立即同步一次
        self.sync_on_startup()
        
        # 启动后台同步线程
        self.sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self.sync_thread.start()
        logger.info("自动同步已启动")
    
    def sync_on_startup(self):
        """启动时的智能同步"""
        logger.info("执行启动同步...")
        
        try:
            # 1. 获取本地最后修改时间
            local_last_modified = self._get_local_last_modified()
            
            # 2. 获取远程最后修改时间
            remote_last_modified = self._get_remote_last_modified()
            
            if remote_last_modified is None:
                # 远程没有数据，上传本地数据
                logger.info("远程仓库为空，上传本地数据")
                self.github_sync.sync_to_github(self.db_path)
            elif local_last_modified is None:
                # 本地没有数据，下载远程数据
                logger.info("本地数据为空，下载远程数据")
                self.github_sync.sync_from_github(self.db_path)
            else:
                # 都有数据，需要智能合并
                self._smart_merge(local_last_modified, remote_last_modified)
                
            self.last_sync_time = datetime.now(timezone.utc)
            self._save_last_sync_time()
            
        except Exception as e:
            logger.error(f"启动同步失败: {e}")
    
    def _smart_merge(self, local_time: datetime, remote_time: datetime):
        """智能合并本地和远程数据"""
        logger.info(f"本地最后修改: {local_time}, 远程最后修改: {remote_time}")
        
        # 确保两个时间都是aware datetime
        if local_time.tzinfo is None:
            local_time = local_time.replace(tzinfo=timezone.utc)
        if remote_time.tzinfo is None:
            remote_time = remote_time.replace(tzinfo=timezone.utc)
        
        # 策略1：如果时间差小于1分钟，认为是同一次修改
        if abs((local_time - remote_time).total_seconds()) < 60:
            logger.info("本地和远程数据时间接近，跳过同步")
            return
            
        # 策略2：如果远程更新，下载并合并
        if remote_time > local_time:
            logger.info("远程数据更新，执行合并...")
            self._merge_from_remote()
        else:
            # 本地更新，上传
            logger.info("本地数据更新，上传到远程")
            self.github_sync.sync_to_github(self.db_path)
    
    def _merge_from_remote(self):
        """从远程合并数据（支持删除同步）"""
        logger.info(f"开始合并远程数据，删除同步: {self.sync_deletions}")
        
        # 1. 备份本地数据
        local_data = self._export_local_data()
        local_ids = {r['id']: r for r in local_data['reflections']}
        local_id_set = set(local_ids.keys())
        
        # 2. 保存当前状态
        original_local_ids = local_id_set.copy()
        
        # 3. 下载远程数据（这会覆盖本地数据库）
        self.github_sync.sync_from_github(self.db_path)
        
        # 4. 获取远程数据的ID集合
        remote_data = self._export_local_data()
        remote_ids = {r['id']: r for r in remote_data['reflections']}
        remote_id_set = set(remote_ids.keys())
        
        # 5. 识别差异
        locally_added = original_local_ids - remote_id_set  # 本地有但远程没有的（本地新增）
        remotely_added = remote_id_set - original_local_ids  # 远程有但本地没有的（远程新增）
        
        # 如果不同步删除，需要恢复本地有但远程没有的记录
        if not self.sync_deletions:
            logger.info(f"删除同步已禁用，将恢复本地记录")
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for reflection_id in locally_added:
                reflection = local_ids[reflection_id]
                # 重新插入本地数据
                tags_str = json.dumps(reflection['tags'], ensure_ascii=False) if reflection['tags'] else "[]"
                cursor.execute('''
                    INSERT OR REPLACE INTO reflections (id, content, summary, tags, category, created_at, updated_at, type)
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
                logger.info(f"恢复本地记录: ID={reflection_id}")
            
            conn.commit()
            conn.close()
            
            # 重新上传，包含本地记录
            self.github_sync.sync_to_github(self.db_path)
        else:
            # 如果启用删除同步，远程的删除会保留（即本地也会删除这些记录）
            logger.info(f"删除同步已启用，本地将同步远程的删除操作")
            if locally_added:
                logger.info(f"以下记录在远程已删除，本地也将删除: {locally_added}")
        
        # 记录同步结果
        logger.info(f"同步完成 - 新增: {len(remotely_added)}, 删除: {len(locally_added) if self.sync_deletions else 0}")
    
    def _get_local_last_modified(self) -> datetime:
        """获取本地数据最后修改时间"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT MAX(updated_at) FROM reflections
        ''')
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0]:
            # 确保返回的是UTC时间
            dt = datetime.fromisoformat(result[0])
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        return None
    
    def _get_remote_last_modified(self) -> datetime:
        """获取远程数据最后修改时间"""
        try:
            # 获取最新备份文件的提交时间
            contents = self.github_sync.repo.get_contents("", ref=self.github_sync.branch)
            backup_files = [f for f in contents if f.name.startswith("reflections_backup_") and f.name.endswith(".json")]
            
            if not backup_files:
                return None
                
            # 获取最新文件的最后提交
            latest_file = max(backup_files, key=lambda x: x.name)
            commits = self.github_sync.repo.get_commits(path=latest_file.path)
            
            if commits.totalCount > 0:
                latest_commit = commits[0]
                return latest_commit.commit.author.date
                
        except Exception as e:
            logger.error(f"获取远程修改时间失败: {e}")
            
        return None
    
    def _export_local_data(self) -> dict:
        """导出本地数据"""
        json_str = self.github_sync.export_to_json(self.db_path)
        return json.loads(json_str)
    
    def _sync_loop(self):
        """后台同步循环"""
        while True:
            time.sleep(self.sync_interval)
            
            if not self.is_syncing:
                self.is_syncing = True
                try:
                    logger.info("执行定期同步...")
                    
                    # 检查本地是否有新变化
                    local_modified = self._get_local_last_modified()
                    if local_modified and self.last_sync_time:
                        if local_modified > self.last_sync_time:
                            # 有新变化，上传
                            self.github_sync.sync_to_github(self.db_path)
                            self.last_sync_time = datetime.now(timezone.utc)
                            self._save_last_sync_time()
                            self._notify_sync_complete()
                            
                except Exception as e:
                    logger.error(f"自动同步失败: {e}")
                finally:
                    self.is_syncing = False
    
    def add_sync_callback(self, callback):
        """添加同步完成回调"""
        self.sync_callbacks.append(callback)
    
    def _notify_sync_complete(self):
        """通知同步完成"""
        for callback in self.sync_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"同步回调执行失败: {e}")
    
    def manual_sync(self, direction: str = "both") -> bool:
        """手动触发同步"""
        if self.is_syncing:
            logger.warning("正在同步中，请稍候...")
            return False
            
        self.is_syncing = True
        try:
            if direction == "upload":
                success = self.github_sync.sync_to_github(self.db_path)
            elif direction == "download":
                success = self.github_sync.sync_from_github(self.db_path)
            else:  # both
                self.sync_on_startup()
                success = True
                
            if success:
                self.last_sync_time = datetime.now(timezone.utc)
                self._save_last_sync_time()
                self._notify_sync_complete()
                
            return success
            
        finally:
            self.is_syncing = False
    
    def get_sync_status(self) -> Dict:
        """获取同步状态"""
        return {
            'is_configured': self.github_sync.is_configured(),
            'is_syncing': self.is_syncing,
            'last_sync_time': self.last_sync_time,
            'auto_sync_enabled': self.sync_thread and self.sync_thread.is_alive()
        }
    
    def _save_last_sync_time(self):
        """保存上次同步时间到文件"""
        try:
            sync_state = {
                'last_sync_time': self.last_sync_time.isoformat() if self.last_sync_time else None
            }
            with open(self.sync_state_file, 'w') as f:
                json.dump(sync_state, f)
        except Exception as e:
            logger.error(f"保存同步状态失败: {e}")
    
    def _load_last_sync_time(self) -> Optional[datetime]:
        """从文件加载上次同步时间"""
        try:
            if self.sync_state_file.exists():
                with open(self.sync_state_file, 'r') as f:
                    sync_state = json.load(f)
                    if sync_state.get('last_sync_time'):
                        # 解析ISO格式的时间字符串
                        dt = datetime.fromisoformat(sync_state['last_sync_time'])
                        # 确保时间有时区信息
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        return dt
        except Exception as e:
            logger.error(f"加载同步状态失败: {e}")
        return None 