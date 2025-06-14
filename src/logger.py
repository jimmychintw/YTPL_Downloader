"""
日誌模組 - 提供統一的日誌記錄接口

功能：
- 統一的日誌格式化
- 支援多種日誌層級
- 可同時輸出到控制台和檔案
- 包含豐富的上下文資訊
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """彩色日誌格式化器，讓控制台輸出更易讀"""
    
    # ANSI 顏色碼
    COLORS = {
        'DEBUG': '\033[36m',     # 青色
        'INFO': '\033[32m',      # 綠色
        'WARNING': '\033[33m',   # 黃色
        'ERROR': '\033[31m',     # 紅色
        'CRITICAL': '\033[35m',  # 紫色
    }
    RESET = '\033[0m'
    
    def format(self, record):
        # 建立 record 的副本以避免修改原始物件
        record_copy = logging.makeLogRecord(record.__dict__)
        
        # 為日誌等級添加顏色
        levelname = record_copy.levelname
        if levelname in self.COLORS:
            record_copy.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
        
        # 為模組名稱添加顏色
        record_copy.name = f"\033[34m{record_copy.name}\033[0m"
        
        return super().format(record_copy)


def setup_logger(
    name: str = 'YTPL_Downloader',
    level: str = 'INFO',
    log_file: Optional[str] = None,
    console_output: bool = True
) -> logging.Logger:
    """
    設定並返回日誌記錄器
    
    Args:
        name: 日誌記錄器名稱
        level: 日誌層級 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 可選的日誌檔案路徑
        console_output: 是否輸出到控制台
        
    Returns:
        配置好的日誌記錄器
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # 清除現有的處理器
    logger.handlers.clear()
    
    # 日誌格式
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # 控制台處理器
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper()))
        
        # 使用彩色格式化器
        console_formatter = ColoredFormatter(log_format, datefmt=date_format)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    # 檔案處理器
    if log_file:
        # 確保日誌目錄存在
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(getattr(logging, level.upper()))
        
        # 檔案使用普通格式化器
        file_formatter = logging.Formatter(log_format, datefmt=date_format)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    獲取指定名稱的日誌記錄器
    
    Args:
        name: 模組名稱
        
    Returns:
        日誌記錄器實例
    """
    return logging.getLogger(f'YTPL_Downloader.{name}')