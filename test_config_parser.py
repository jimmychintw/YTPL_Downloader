#!/usr/bin/env python3
"""測試 config_parser.py 模組"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config_parser import ConfigParser
from logger import setup_logger

# 設定日誌
logger = setup_logger(level='DEBUG')

def test_config_parser():
    """測試配置解析器"""
    print("=== 測試配置解析器 ===\n")
    
    # 建立解析器實例
    parser = ConfigParser('config.ini')
    
    try:
        # 載入配置
        parser.load()
        print("✓ 配置載入成功\n")
        
        # 顯示通用配置
        general = parser.get_general_config()
        print("=== General 配置 ===")
        print(f"Client Secrets: {general.client_secrets_file}")
        print(f"Token Storage: {general.token_storage_file}")
        print(f"Check Interval: {general.check_interval_seconds} 秒\n")
        
        # 顯示 Playlist 配置
        playlists = parser.get_playlist_configs()
        print(f"=== Playlist 配置 (共 {len(playlists)} 個) ===")
        for playlist in playlists:
            print(f"\n[{playlist.name}]")
            print(f"  URL: {playlist.playlist_url}")
            print(f"  下載目錄: {playlist.download_directory}")
        
        # 測試取得特定 playlist
        print("\n=== 測試取得特定 Playlist ===")
        test_name = "Translation"
        specific = parser.get_playlist_config(test_name)
        if specific:
            print(f"✓ 找到 '{test_name}' playlist")
        else:
            print(f"✗ 找不到 '{test_name}' playlist")
            
    except Exception as e:
        print(f"\n✗ 錯誤: {e}")
        return False
    
    print("\n✓ 所有測試通過")
    return True

if __name__ == "__main__":
    test_config_parser()