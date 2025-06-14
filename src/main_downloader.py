"""
主下載統籌模組 - 整合所有組件，實現完整的 YouTube Playlist 自動化下載流程

功能：
- 統籌所有已完成的模組
- 實現完整的業務邏輯流程
- 自動監控 Playlist 並下載新影片
- 下載完成後自動從雲端移除
"""

import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Set
from datetime import datetime

from logger import setup_logger, get_logger
from config_parser import ConfigParser
from file_manager import FileManager
from youtube_api_client import YouTubeAPIClient
from video_downloader import VideoDownloader
from googleapiclient.errors import HttpError

logger = get_logger('main_downloader')


class MainDownloader:
    """主下載統籌器 - 整合所有組件的核心引擎"""
    
    def __init__(self):
        """初始化主下載器"""
        self.config_parser: ConfigParser = None
        self.file_manager: FileManager = None
        self.youtube_api_client: YouTubeAPIClient = None
        self.video_downloader: VideoDownloader = None
        
        logger.info("MainDownloader 初始化開始")
    
    def initialize(self, config_file: str = "config.ini") -> bool:
        """
        初始化所有模組
        
        Args:
            config_file: 配置檔案路徑
            
        Returns:
            是否初始化成功
        """
        logger.info("=== 初始化階段開始 ===")
        
        try:
            # 1. 載入配置
            logger.info("載入配置檔案...")
            self.config_parser = ConfigParser(config_file)
            self.config_parser.load()
            
            # ConfigParser.load() 沒有返回值，如果成功會正常執行，失敗會拋出異常
            
            logger.info(f"配置載入成功: {len(self.config_parser.playlist_configs)} 個 Playlist")
            
            # 2. 初始化 FileManager
            logger.info("初始化檔案管理器...")
            self.file_manager = FileManager()
            logger.info("檔案管理器初始化成功")
            
            # 3. 初始化 YouTubeAPIClient
            logger.info("初始化 YouTube API 客戶端...")
            general_config = self.config_parser.get_general_config()
            self.youtube_api_client = YouTubeAPIClient(
                client_secrets_file=str(Path(general_config.client_secrets_file)),
                token_storage_file=str(Path(general_config.token_storage_file))
            )
            logger.info("YouTube API 客戶端初始化成功")
            
            # 4. 初始化 VideoDownloader
            logger.info("初始化影片下載器...")
            self.video_downloader = VideoDownloader()
            logger.info("影片下載器初始化成功")
            
            logger.info("=== 初始化階段完成 ===")
            return True
            
        except FileNotFoundError as e:
            logger.error(f"配置檔案錯誤: {e}")
            return False
        except ValueError as e:
            logger.error(f"配置格式錯誤: {e}")
            return False
        except RuntimeError as e:
            logger.error(f"模組初始化錯誤: {e}")
            return False
        except Exception as e:
            logger.error(f"未知的初始化錯誤: {e}")
            return False
    
    def authenticate(self) -> bool:
        """
        執行 YouTube API 認證
        
        Returns:
            是否認證成功
        """
        logger.info("=== 認證階段開始 ===")
        
        try:
            if not self.youtube_api_client.authenticate():
                logger.error("YouTube API 認證失敗")
                return False
            
            logger.info("YouTube API 認證成功")
            logger.info("=== 認證階段完成 ===")
            return True
            
        except HttpError as e:
            logger.error(f"YouTube API 認證錯誤: {e}")
            return False
        except FileNotFoundError as e:
            logger.error(f"認證檔案錯誤: {e}")
            return False
        except Exception as e:
            logger.error(f"未知的認證錯誤: {e}")
            return False
    
    def run_single_cycle(self) -> Dict[str, Any]:
        """
        執行單次完整的下載循環
        
        Returns:
            執行結果統計
        """
        cycle_start_time = datetime.now()
        logger.info("=== 主循環開始 ===")
        
        # 初始化統計數據
        cycle_stats = {
            "start_time": cycle_start_time.isoformat(),
            "end_time": None,
            "duration_seconds": 0,
            "playlists_processed": 0,
            "total_videos_found": 0,
            "total_videos_downloaded": 0,
            "total_videos_removed": 0,
            "successful_playlists": 0,
            "failed_playlists": 0,
            "playlist_results": []
        }
        
        try:
            # 遍歷所有 Playlist
            for playlist_config in self.config_parser.playlist_configs:
                logger.info(f"開始處理 Playlist: {playlist_config.name}")
                cycle_stats["playlists_processed"] += 1
                
                playlist_result = self._process_single_playlist(playlist_config)
                cycle_stats["playlist_results"].append(playlist_result)
                
                # 累計統計
                cycle_stats["total_videos_found"] += playlist_result["videos_found"]
                cycle_stats["total_videos_downloaded"] += playlist_result["videos_downloaded"]
                cycle_stats["total_videos_removed"] += playlist_result["videos_removed"]
                
                if playlist_result["success"]:
                    cycle_stats["successful_playlists"] += 1
                else:
                    cycle_stats["failed_playlists"] += 1
                
                logger.info(f"Playlist 處理完成: {playlist_config.name}")
            
            # 計算總耗時
            cycle_end_time = datetime.now()
            cycle_stats["end_time"] = cycle_end_time.isoformat()
            cycle_stats["duration_seconds"] = (cycle_end_time - cycle_start_time).total_seconds()
            
            # 輸出週期摘要
            self._log_cycle_summary(cycle_stats)
            
            logger.info("=== 主循環完成 ===")
            return cycle_stats
            
        except Exception as e:
            logger.error(f"主循環過程中發生錯誤: {e}")
            cycle_stats["error"] = str(e)
            return cycle_stats
    
    def _process_single_playlist(self, playlist_config) -> Dict[str, Any]:
        """
        處理單個 Playlist 的完整流程
        
        Args:
            playlist_config: Playlist 配置
            
        Returns:
            處理結果統計
        """
        playlist_start_time = datetime.now()
        playlist_result = {
            "playlist_name": playlist_config.name,
            "playlist_url": playlist_config.playlist_url,
            "start_time": playlist_start_time.isoformat(),
            "end_time": None,
            "duration_seconds": 0,
            "success": False,
            "videos_found": 0,
            "videos_downloaded": 0,
            "videos_removed": 0,
            "downloaded_videos": [],
            "error": None
        }
        
        try:
            logger.info(f"📥 獲取 Playlist 影片列表: {playlist_config.name}")
            
            # 1. 獲取雲端影片列表
            cloud_videos = self.youtube_api_client.get_playlist_videos(playlist_config.playlist_url)
            if not cloud_videos:
                logger.warning(f"Playlist 中沒有找到影片: {playlist_config.name}")
                playlist_result["success"] = True
                return playlist_result
            
            playlist_result["videos_found"] = len(cloud_videos)
            logger.info(f"找到 {len(cloud_videos)} 個影片")
            
            # 2. 掃描本地已下載的影片
            logger.info("🔍 掃描本地已下載影片...")
            local_video_ids = self.file_manager.scan_downloaded_video_ids(
                Path(playlist_config.download_directory)
            )
            logger.info(f"本地已有 {len(local_video_ids)} 個影片")
            
            # 3. 識別需要下載的新影片
            new_videos = []
            for video in cloud_videos:
                if video['video_id'] not in local_video_ids:
                    new_videos.append(video)
            
            if not new_videos:
                logger.info(f"沒有新影片需要下載: {playlist_config.name}")
                playlist_result["success"] = True
                return playlist_result
            
            logger.info(f"🆕 發現 {len(new_videos)} 個新影片需要下載")
            
            # 4. 從已獲取的影片列表中直接建立映射（避免冗餘 API 調用）
            logger.info("🗺️  建立影片映射表...")
            video_id_to_item_id = {video['video_id']: video['playlist_item_id'] for video in cloud_videos}
            
            # 5. 處理每個新影片
            for i, video in enumerate(new_videos, 1):
                logger.info(f"📺 處理影片 ({i}/{len(new_videos)}): {video['title']}")
                
                try:
                    # 為影片建立獨立資料夾
                    video_folder = self.file_manager.create_video_folder(
                        base_path=Path(playlist_config.download_directory),
                        video_id=video['video_id'],
                        video_title=video['title']
                    )
                    
                    # 建構影片 URL
                    video_url = f"https://www.youtube.com/watch?v={video['video_id']}"
                    
                    # 執行完整下載流程
                    download_success, performance_data = self.video_downloader.download_video_complete(
                        video_url=video_url,
                        video_id=video['video_id'],
                        output_dir=video_folder,
                        file_manager=self.file_manager
                    )
                    
                    if download_success:
                        playlist_result["videos_downloaded"] += 1
                        logger.info(f"✅ 下載成功: {video['title']}")
                        
                        # 從雲端 Playlist 移除
                        if video['video_id'] in video_id_to_item_id:
                            playlist_item_id = video_id_to_item_id[video['video_id']]
                            
                            if self.youtube_api_client.remove_video_from_playlist(playlist_item_id):
                                playlist_result["videos_removed"] += 1
                                logger.info(f"🗑️  已從 Playlist 移除: {video['title']}")
                            else:
                                logger.warning(f"⚠️  無法從 Playlist 移除: {video['title']}")
                        else:
                            logger.warning(f"⚠️  找不到 playlist_item_id: {video['video_id']}")
                        
                        # 記錄成功下載的影片
                        playlist_result["downloaded_videos"].append({
                            "video_id": video['video_id'],
                            "title": video['title'],
                            "folder_path": str(video_folder.absolute()),
                            "performance_data": performance_data
                        })
                        
                        # 🎯 輸出成功下載的資料夾絕對路徑（按需求規格）
                        print(video_folder.absolute())
                        
                    else:
                        logger.error(f"❌ 下載失敗: {video['title']}")
                        
                except Exception as e:
                    logger.error(f"處理影片時發生錯誤: {video['title']} - {e}")
                    continue
            
            # 計算耗時
            playlist_end_time = datetime.now()
            playlist_result["end_time"] = playlist_end_time.isoformat()
            playlist_result["duration_seconds"] = (playlist_end_time - playlist_start_time).total_seconds()
            playlist_result["success"] = True
            
            logger.info(f"🎉 Playlist 處理完成: {playlist_config.name}")
            logger.info(f"   下載: {playlist_result['videos_downloaded']} 個影片")
            logger.info(f"   移除: {playlist_result['videos_removed']} 個影片")
            
            return playlist_result
            
        except Exception as e:
            logger.error(f"處理 Playlist 時發生錯誤: {playlist_config.name} - {e}")
            playlist_result["error"] = str(e)
            return playlist_result
    
    def _log_cycle_summary(self, cycle_stats: Dict[str, Any]) -> None:
        """
        記錄週期執行摘要
        
        Args:
            cycle_stats: 週期統計數據
        """
        logger.info("=" * 60)
        logger.info("🏁 本次執行週期摘要")
        logger.info("=" * 60)
        logger.info(f"⏱️  執行耗時: {cycle_stats['duration_seconds']:.2f} 秒")
        logger.info(f"📂 處理的 Playlist: {cycle_stats['playlists_processed']} 個")
        logger.info(f"✅ 成功處理: {cycle_stats['successful_playlists']} 個")
        logger.info(f"❌ 失敗處理: {cycle_stats['failed_playlists']} 個")
        logger.info(f"🔍 發現影片總數: {cycle_stats['total_videos_found']} 個")
        logger.info(f"📥 下載影片總數: {cycle_stats['total_videos_downloaded']} 個")
        logger.info(f"🗑️  移除影片總數: {cycle_stats['total_videos_removed']} 個")
        
        if cycle_stats['total_videos_downloaded'] > 0:
            logger.info("\n📺 本次下載的影片資料夾:")
            for playlist_result in cycle_stats['playlist_results']:
                for video in playlist_result.get('downloaded_videos', []):
                    logger.info(f"   📁 {video['folder_path']}")
        
        logger.info("=" * 60)
    
    def run_continuous(self, interval_minutes: int = 60) -> None:
        """
        持續運行模式 - 定期執行下載循環
        
        Args:
            interval_minutes: 執行間隔（分鐘）
        """
        logger.info(f"🔄 啟動持續運行模式 (間隔: {interval_minutes} 分鐘)")
        
        while True:
            try:
                # 執行單次循環
                cycle_stats = self.run_single_cycle()
                
                # 等待下次執行
                logger.info(f"⏳ 等待 {interval_minutes} 分鐘後執行下次循環...")
                time.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                logger.info("👋 收到中斷信號，正在停止...")
                break
            except Exception as e:
                logger.error(f"持續運行模式中發生錯誤: {e}")
                logger.info(f"⏳ 等待 {interval_minutes} 分鐘後重試...")
                time.sleep(interval_minutes * 60)


def main():
    """主入口函數"""
    # 設定日誌
    setup_logger(level='INFO')
    logger.info("🚀 YTPL_Downloader 啟動")
    
    try:
        # 創建主下載器
        downloader = MainDownloader()
        
        # 初始化
        if not downloader.initialize():
            logger.error("初始化失敗，程式退出")
            sys.exit(1)
        
        # 認證
        if not downloader.authenticate():
            logger.error("認證失敗，程式退出")
            sys.exit(1)
        
        # 執行單次循環（可以根據需要改為持續運行）
        cycle_stats = downloader.run_single_cycle()
        
        # 根據結果決定退出碼
        if cycle_stats.get('failed_playlists', 0) > 0:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except KeyboardInterrupt:
        logger.info("👋 程式被用戶中斷")
        sys.exit(0)
    except Exception as e:
        logger.error(f"程式執行中發生未預期錯誤: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()