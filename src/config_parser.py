"""
配置檔解析模組 - 讀取和解析 config.ini

功能：
- 讀取 INI 格式配置檔
- 驗證必要欄位
- 提供結構化的配置資料
- 處理預設值和錯誤情況
"""

import configparser
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs

from logger import get_logger

logger = get_logger('config_parser')


@dataclass
class PlaylistConfig:
    """單個 Playlist 的配置資料"""
    name: str
    playlist_url: str
    download_directory: str
    
    def __post_init__(self):
        """驗證配置資料"""
        # 驗證 YouTube Playlist URL 格式
        try:
            parsed_url = urlparse(self.playlist_url)
            if not (parsed_url.netloc in ['www.youtube.com', 'youtube.com'] and 
                    parsed_url.path == '/playlist' and 
                    'list' in parse_qs(parsed_url.query)):
                raise ValueError(f"無效的 YouTube Playlist URL: {self.playlist_url}")
        except Exception as e:
            raise ValueError(f"無法解析 Playlist URL: {self.playlist_url} - {e}")
        
        # 確保下載目錄存在
        Path(self.download_directory).mkdir(parents=True, exist_ok=True)


@dataclass
class GeneralConfig:
    """通用配置資料"""
    client_secrets_file: str
    token_storage_file: str
    check_interval_seconds: int = 60
    
    def __post_init__(self):
        """驗證配置資料"""
        if not Path(self.client_secrets_file).exists():
            raise FileNotFoundError(f"找不到 client_secrets 檔案: {self.client_secrets_file}")
        
        if self.check_interval_seconds < 1:
            raise ValueError("check_interval_seconds 必須大於 0")


class ConfigParser:
    """配置檔解析器"""
    
    def __init__(self, config_file: str = 'config.ini'):
        """
        初始化配置解析器
        
        Args:
            config_file: 配置檔路徑
        """
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.general_config: Optional[GeneralConfig] = None
        self.playlist_configs: List[PlaylistConfig] = []
        
    def load(self) -> None:
        """載入並解析配置檔"""
        if not Path(self.config_file).exists():
            raise FileNotFoundError(f"找不到配置檔: {self.config_file}")
        
        logger.info(f"載入配置檔: {self.config_file}")
        
        # 讀取配置檔
        self.config.read(self.config_file, encoding='utf-8')
        
        # 解析通用配置
        self._parse_general_config()
        
        # 解析 Playlist 配置
        self._parse_playlist_configs()
        
        logger.info(f"成功載入 {len(self.playlist_configs)} 個 playlist 配置")
        
    def _parse_general_config(self) -> None:
        """解析 [General] 區塊"""
        if 'General' not in self.config:
            raise ValueError("配置檔缺少 [General] 區塊")
        
        general = self.config['General']
        
        try:
            self.general_config = GeneralConfig(
                client_secrets_file=general.get('client_secrets_file'),
                token_storage_file=general.get('token_storage_file'),
                check_interval_seconds=general.getint('check_interval_seconds', 60)
            )
            logger.debug("General 配置載入成功")
        except (KeyError, ValueError) as e:
            raise ValueError(f"General 配置錯誤: {e}")
    
    def _parse_playlist_configs(self) -> None:
        """解析所有 [Playlist_*] 區塊"""
        self.playlist_configs = []
        
        for section in self.config.sections():
            if section.startswith('Playlist_'):
                playlist_name = section[9:]  # 移除 'Playlist_' 前綴
                
                try:
                    playlist_config = PlaylistConfig(
                        name=playlist_name,
                        playlist_url=self.config[section].get('playlist_url'),
                        download_directory=self.config[section].get('download_directory')
                    )
                    self.playlist_configs.append(playlist_config)
                    logger.debug(f"載入 playlist 配置: {playlist_name}")
                    
                except (KeyError, ValueError) as e:
                    logger.error(f"Playlist {playlist_name} 配置錯誤: {e}")
                    raise ValueError(f"Playlist {playlist_name} 配置錯誤: {e}")
    
    def get_general_config(self) -> GeneralConfig:
        """取得通用配置"""
        if not self.general_config:
            raise RuntimeError("配置尚未載入，請先呼叫 load()")
        return self.general_config
    
    def get_playlist_configs(self) -> List[PlaylistConfig]:
        """取得所有 Playlist 配置"""
        if not self.playlist_configs:
            logger.warning("沒有找到任何 playlist 配置")
        return self.playlist_configs
    
    def get_playlist_config(self, name: str) -> Optional[PlaylistConfig]:
        """
        取得特定名稱的 Playlist 配置
        
        Args:
            name: Playlist 名稱
            
        Returns:
            PlaylistConfig 或 None
        """
        for config in self.playlist_configs:
            if config.name == name:
                return config
        return None