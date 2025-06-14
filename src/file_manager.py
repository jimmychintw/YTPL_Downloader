"""
檔案管理模組 - 處理本地檔案系統操作

功能：
- 創建影片子資料夾
- 標準化檔案命名
- 讀寫 video_info.json
- 掃描已下載影片 ID
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from logger import get_logger

logger = get_logger('file_manager')


class FileManager:
    """檔案管理器 - 處理所有本地檔案系統操作"""
    
    def __init__(self):
        """初始化檔案管理器"""
        pass
    
    def sanitize_filename(self, title: str, max_length: int = 50) -> str:
        """
        淨化檔案名稱，移除特殊字符
        
        Args:
            title: 原始標題
            max_length: 最大長度限制
            
        Returns:
            淨化後的檔案名稱
        """
        if not title:
            return "untitled"
            
        # 移除前後空白
        sanitized = title.strip()
        
        # 替換特殊字符和空白為底線
        sanitized = re.sub(r'[/\\:*?"<>|\s]', '_', sanitized)
        
        # 限制長度
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        # 合併連續底線
        sanitized = re.sub(r'_+', '_', sanitized)
        
        # 移除開頭和結尾的底線
        sanitized = sanitized.strip('_')
        
        # 如果處理後為空，返回預設值
        if not sanitized:
            return "untitled"
            
        return sanitized
    
    def generate_folder_name(self, title: str, video_id: str, date: Optional[datetime] = None) -> str:
        """
        生成標準化的資料夾名稱
        
        格式：[YYYY-MM-DD]_[sanitized_title]_[video_id]
        
        Args:
            title: 影片標題
            video_id: YouTube 影片 ID
            date: 日期（預設為今天）
            
        Returns:
            標準化的資料夾名稱
        """
        if date is None:
            date = datetime.now()
        
        date_str = date.strftime('%Y-%m-%d')
        sanitized_title = self.sanitize_filename(title)
        
        return f"{date_str}_{sanitized_title}_{video_id}"
    
    def create_video_folder(self, download_directory: str, title: str, video_id: str) -> Path:
        """
        創建影片子資料夾
        
        Args:
            download_directory: 下載根目錄
            title: 影片標題
            video_id: YouTube 影片 ID
            
        Returns:
            創建的資料夾路徑
            
        Raises:
            OSError: 無法創建資料夾時
        """
        download_path = Path(download_directory)
        folder_name = self.generate_folder_name(title, video_id)
        video_folder = download_path / folder_name
        
        try:
            video_folder.mkdir(parents=True, exist_ok=True)
            logger.info(f"創建影片資料夾: {video_folder}")
            return video_folder
        except OSError as e:
            logger.error(f"無法創建資料夾 {video_folder}: {e}")
            raise
    
    def write_video_info(self, folder_path: Path, video_info: Dict[str, Any]) -> None:
        """
        寫入 video_info.json 檔案
        
        Args:
            folder_path: 影片資料夾路徑
            video_info: 影片資訊字典
            
        Raises:
            OSError: 無法寫入檔案時
            ValueError: video_info 格式錯誤時
        """
        info_file = folder_path / "video_info.json"
        
        try:
            with info_file.open('w', encoding='utf-8') as f:
                json.dump(video_info, f, ensure_ascii=False, indent=2)
            logger.debug(f"寫入 video_info.json: {info_file}")
        except (OSError, TypeError) as e:
            logger.error(f"無法寫入 video_info.json {info_file}: {e}")
            raise
    
    def read_video_info(self, folder_path: Path) -> Optional[Dict[str, Any]]:
        """
        讀取 video_info.json 檔案
        
        Args:
            folder_path: 影片資料夾路徑
            
        Returns:
            影片資訊字典，如果檔案不存在或損壞則返回 None
        """
        info_file = folder_path / "video_info.json"
        
        if not info_file.exists():
            logger.debug(f"video_info.json 不存在: {info_file}")
            return None
        
        try:
            with info_file.open('r', encoding='utf-8') as f:
                video_info = json.load(f)
            logger.debug(f"讀取 video_info.json: {info_file}")
            return video_info
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"無法讀取或解析 video_info.json {info_file}: {e}")
            return None
    
    def extract_video_id(self, video_info: Dict[str, Any]) -> Optional[str]:
        """
        從 video_info 字典中提取 video_id
        
        Args:
            video_info: 影片資訊字典
            
        Returns:
            video_id 或 None
        """
        try:
            # 支援 v1.1 格式：video_id 在 youtube_info 下
            if 'youtube_info' in video_info:
                return video_info['youtube_info'].get('video_id')
            # 向下相容：直接在根層級
            return video_info.get('video_id')
        except (KeyError, AttributeError) as e:
            logger.warning(f"無法提取 video_id: {e}")
            return None
    
    def scan_downloaded_video_ids(self, download_directory: str) -> List[str]:
        """
        掃描下載目錄，收集所有已下載的影片 ID
        
        Args:
            download_directory: 下載根目錄
            
        Returns:
            已下載的影片 ID 列表
        """
        download_path = Path(download_directory)
        video_ids = []
        
        if not download_path.exists():
            logger.warning(f"下載目錄不存在: {download_directory}")
            return video_ids
        
        logger.info(f"掃描下載目錄: {download_directory}")
        
        # 遍歷所有子目錄
        for item in download_path.iterdir():
            if item.is_dir():
                # 嘗試讀取 video_info.json
                video_info = self.read_video_info(item)
                if video_info:
                    video_id = self.extract_video_id(video_info)
                    if video_id:
                        video_ids.append(video_id)
                        logger.debug(f"找到已下載影片: {video_id} ({item.name})")
                    else:
                        logger.warning(f"資料夾 {item.name} 的 video_info.json 缺少 video_id")
                else:
                    logger.debug(f"跳過無 video_info.json 的資料夾: {item.name}")
        
        logger.info(f"掃描完成，找到 {len(video_ids)} 個已下載影片")
        return video_ids