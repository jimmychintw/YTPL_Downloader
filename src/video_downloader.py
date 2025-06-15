"""
影片下載模組 - 作為 yt-dlp 的輕量級包裝器

功能：
- 下載最高解析度影片、所有音軌、所有字幕、縮圖
- 支援斷點續傳
- 實時進度監控和效能記錄
- 完整的錯誤處理和重試機制
"""

import json
import subprocess
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from logger import get_logger

logger = get_logger('video_downloader')


class DownloadProgress:
    """下載進度和效能數據類"""
    
    def __init__(self):
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.total_bytes: int = 0
        self.downloaded_bytes: int = 0
        self.speed_mbps: float = 0.0
        self.eta_seconds: int = 0
        self.percentage: float = 0.0
        self.retry_count: int = 0
        self.status: str = "pending"  # pending, downloading, completed, failed
        
    def start(self):
        """開始下載計時"""
        self.start_time = datetime.now()
        self.status = "downloading"
        
    def complete(self):
        """完成下載"""
        self.end_time = datetime.now()
        self.status = "completed"
        self.percentage = 100.0
        
    def fail(self):
        """下載失敗"""
        self.end_time = datetime.now()
        self.status = "failed"
        self.retry_count += 1
        
    def get_duration_seconds(self) -> float:
        """獲取下載耗時（秒）"""
        if not self.start_time:
            return 0.0
        
        end = self.end_time if self.end_time else datetime.now()
        return (end - self.start_time).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            "download_start_time": self.start_time.isoformat() if self.start_time else None,
            "download_end_time": self.end_time.isoformat() if self.end_time else None,
            "download_duration_seconds": self.get_duration_seconds(),
            "download_status": self.status,
            "retry_count": self.retry_count,
            "total_size_bytes": self.total_bytes,
            "downloaded_bytes": self.downloaded_bytes,
            "average_speed_mbps": self.speed_mbps,
            "progress_percentage": self.percentage
        }


class VideoDownloader:
    """影片下載器 - yt-dlp 包裝器"""
    
    def __init__(self):
        """初始化下載器"""
        self.progress = DownloadProgress()
        
        # 檢查 yt-dlp 是否可用
        if not self._check_yt_dlp_availability():
            raise RuntimeError("yt-dlp 不可用，請確保已正確安裝")
        
        logger.info("VideoDownloader 初始化成功")
    
    def _check_yt_dlp_availability(self) -> bool:
        """檢查 yt-dlp 是否可用"""
        try:
            result = subprocess.run(
                ['yt-dlp', '--version'], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            if result.returncode == 0:
                version = result.stdout.strip()
                logger.info(f"找到 yt-dlp 版本: {version}")
                return True
            else:
                logger.error(f"yt-dlp 檢查失敗: {result.stderr}")
                return False
                
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.error(f"無法找到 yt-dlp: {e}")
            return False
    
    def _build_yt_dlp_command(self, video_url: str, output_dir: Path) -> List[str]:
        """
        建構 yt-dlp 命令列
        
        Args:
            video_url: YouTube 影片 URL
            output_dir: 輸出目錄
            
        Returns:
            yt-dlp 命令列參數列表
        """
        # 基本命令
        cmd = [
            'yt-dlp',
            video_url,
            
            # 輸出設定
            '--output', str(output_dir / '%(title)s.%(ext)s'),
            
            # 品質設定 - 最高解析度
            '--format', 'best[height<=?2160]',  # 最高 4K，避免超大檔案
            
            # 字幕設定 - 只下載英文和中文字幕
            '--write-subs',           # 下載字幕
            '--write-auto-subs',      # 下載自動生成字幕
            '--sub-langs', 'en.*,zh.*',  # 只下載英文和中文系列字幕
            '--write-thumbnail',      # 下載縮圖
            
            # 元數據設定
            '--write-info-json',      # 輸出詳細資訊 JSON
            '--write-description',    # 下載描述
            
            # 斷點續傳設定
            '--continue',             # 啟用斷點續傳
            '--no-overwrites',        # 避免覆寫已存在檔案
            '--part',                 # 保留 .part 檔案以供續傳
            
            # 進度輸出設定
            '--newline',              # 每行一個進度更新
            '--progress',             # 顯示進度
            
            # 重試設定
            '--retries', '3',         # 重試 3 次
            '--fragment-retries', '3', # 片段重試 3 次
            
            # 網路設定
            '--socket-timeout', '30', # Socket 超時 30 秒
        ]
        
        logger.debug(f"建構 yt-dlp 命令: {' '.join(cmd)}")
        return cmd
    
    def _parse_progress_line(self, line: str) -> None:
        """
        解析 yt-dlp 進度輸出行
        
        Args:
            line: yt-dlp 輸出的一行
        """
        line = line.strip()
        if not line:
            return
        
        # 解析下載進度
        # 格式範例: [download]  45.2% of  123.45MiB at  1.23MiB/s ETA 00:42
        if '[download]' in line and '%' in line:
            try:
                # 提取百分比
                percent_match = re.search(r'(\d+\.?\d*)%', line)
                if percent_match:
                    self.progress.percentage = float(percent_match.group(1))
                
                # 提取總大小
                size_match = re.search(r'of\s+([\d.]+)(MiB|GiB|KiB|B)', line)
                if size_match:
                    size_value = float(size_match.group(1))
                    size_unit = size_match.group(2)
                    
                    # 轉換為 bytes
                    unit_multipliers = {
                        'B': 1,
                        'KiB': 1024,
                        'MiB': 1024 * 1024,
                        'GiB': 1024 * 1024 * 1024
                    }
                    
                    if size_unit in unit_multipliers:
                        self.progress.total_bytes = int(size_value * unit_multipliers[size_unit])
                
                # 提取下載速度
                speed_match = re.search(r'at\s+([\d.]+)(MiB|GiB|KiB|B)/s', line)
                if speed_match:
                    speed_value = float(speed_match.group(1))
                    speed_unit = speed_match.group(2)
                    
                    # 轉換為 Mbps
                    if speed_unit == 'MiB':
                        self.progress.speed_mbps = speed_value * 8  # MiB/s to Mbps
                    elif speed_unit == 'GiB':
                        self.progress.speed_mbps = speed_value * 8 * 1024
                    elif speed_unit == 'KiB':
                        self.progress.speed_mbps = speed_value * 8 / 1024
                    elif speed_unit == 'B':
                        self.progress.speed_mbps = speed_value * 8 / (1024 * 1024)
                
                # 提取 ETA
                eta_match = re.search(r'ETA\s+(\d+):(\d+)', line)
                if eta_match:
                    minutes = int(eta_match.group(1))
                    seconds = int(eta_match.group(2))
                    self.progress.eta_seconds = minutes * 60 + seconds
                
                # 計算已下載大小
                if self.progress.total_bytes > 0:
                    self.progress.downloaded_bytes = int(
                        self.progress.total_bytes * self.progress.percentage / 100
                    )
                
                # 記錄進度到日誌
                if self.progress.percentage > 0:
                    logger.debug(
                        f"下載進度: {self.progress.percentage:.1f}% "
                        f"({self.progress.downloaded_bytes}/{self.progress.total_bytes} bytes) "
                        f"速度: {self.progress.speed_mbps:.2f} Mbps"
                    )
                    
            except (ValueError, AttributeError) as e:
                logger.debug(f"解析進度行失敗: {line} - {e}")
        
        # 記錄其他重要輸出
        if any(keyword in line.lower() for keyword in ['error', 'warning', 'failed']):
            logger.warning(f"yt-dlp 輸出: {line}")
        elif '[info]' in line:
            logger.info(f"yt-dlp: {line}")
        else:
            logger.debug(f"yt-dlp: {line}")
    
    def download_video(self, video_url: str, output_dir: Path) -> bool:
        """
        下載影片的主要方法
        
        Args:
            video_url: YouTube 影片 URL
            output_dir: 輸出目錄
            
        Returns:
            是否下載成功
        """
        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"開始下載影片: {video_url}")
        logger.info(f"輸出目錄: {output_dir}")
        
        # 重置進度
        self.progress = DownloadProgress()
        self.progress.start()
        
        # 建構命令
        cmd = self._build_yt_dlp_command(video_url, output_dir)
        
        try:
            # 執行 yt-dlp
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # 即時處理輸出
            for line in process.stdout:
                self._parse_progress_line(line)
            
            # 等待完成
            return_code = process.wait()
            
            if return_code == 0:
                self.progress.complete()
                logger.info(f"影片下載成功: {video_url}")
                logger.info(f"下載耗時: {self.progress.get_duration_seconds():.2f} 秒")
                logger.info(f"平均速度: {self.progress.speed_mbps:.2f} Mbps")
                return True
            else:
                self.progress.fail()
                logger.error(f"影片下載失敗，返回碼: {return_code}")
                return False
                
        except subprocess.TimeoutExpired:
            self.progress.fail()
            logger.error("下載超時")
            if process:
                process.kill()
            return False
        except Exception as e:
            self.progress.fail()
            logger.error(f"下載過程中發生錯誤: {e}")
            return False
    
    def download_video_with_retry(self, video_url: str, output_dir: Path, max_retries: int = 3) -> bool:
        """
        帶重試機制的下載方法
        
        Args:
            video_url: YouTube 影片 URL
            output_dir: 輸出目錄
            max_retries: 最大重試次數
            
        Returns:
            是否最終下載成功
        """
        for attempt in range(max_retries + 1):
            if attempt > 0:
                logger.info(f"重試下載 (嘗試 {attempt}/{max_retries}): {video_url}")
                # 重試前短暫等待
                time.sleep(min(5 * attempt, 30))  # 遞增等待時間，最多 30 秒
            
            success = self.download_video(video_url, output_dir)
            
            if success:
                if attempt > 0:
                    logger.info(f"重試成功！(共嘗試 {attempt + 1} 次)")
                return True
            
            if attempt < max_retries:
                logger.warning(f"下載失敗，將重試... (剩餘 {max_retries - attempt} 次)")
        
        logger.error(f"下載最終失敗，已重試 {max_retries} 次: {video_url}")
        return False
    
    def download_video_complete(self, video_url: str, video_id: str, output_dir: Path, 
                               file_manager) -> Tuple[bool, Dict[str, Any]]:
        """
        完整的下載流程，包含 video_info.json 更新
        
        Args:
            video_url: YouTube 影片 URL
            video_id: 影片 ID
            output_dir: 輸出目錄
            file_manager: FileManager 實例
            
        Returns:
            (是否成功, 效能數據字典)
        """
        logger.info(f"開始完整下載流程: {video_id}")
        
        # 1. 嘗試下載（帶重試）
        success = self.download_video_with_retry(video_url, output_dir)
        
        # 2. 準備效能數據
        performance_data = {
            **self.progress.to_dict(),
            "download_timestamp": datetime.now().isoformat(),
            "video_id": video_id,
            "video_url": video_url
        }
        
        # 3. 檢查下載結果並更新 video_info.json
        if success:
            try:
                # 🔥 核心優化：使用 yt-dlp 生成的 .info.json 作為單一事實來源
                info_json_path = self._find_info_json_file(output_dir)
                if not info_json_path:
                    logger.error("找不到 yt-dlp 生成的 .info.json 檔案")
                    return False, performance_data
                
                # 從 .info.json 提取完整的 YouTube 資訊
                youtube_info = self._extract_youtube_info_from_json(info_json_path)
                if not youtube_info:
                    logger.error("無法從 .info.json 提取 YouTube 資訊")
                    return False, performance_data
                
                # 基於 .info.json 精確掃描下載的檔案
                downloaded_files = self._scan_downloaded_files_from_info_json(output_dir, info_json_path)
                
                # 建立符合 SDD v1.1 格式的 video_info
                video_info = self._create_video_info_json(
                    youtube_info=youtube_info,
                    downloaded_files=downloaded_files,
                    performance_data=performance_data
                )
                
                # 寫入 video_info.json
                file_manager.write_video_info(output_dir, video_info)
                
                logger.info(f"完整下載流程成功完成: {youtube_info.get('title', video_id)}")
                return True, performance_data
                
            except Exception as e:
                logger.error(f"下載後處理失敗: {e}")
                return False, performance_data
        else:
            logger.error(f"下載失敗: {video_id}")
            return False, performance_data
    
    def _find_info_json_file(self, output_dir: Path) -> Optional[Path]:
        """
        尋找 yt-dlp 生成的 .info.json 檔案
        
        Args:
            output_dir: 輸出目錄
            
        Returns:
            .info.json 檔案路徑或 None
        """
        if not output_dir.exists():
            return None
        
        # 尋找 .info.json 檔案
        for file_path in output_dir.iterdir():
            if file_path.is_file() and file_path.name.endswith('.info.json'):
                logger.debug(f"找到 info.json 檔案: {file_path.name}")
                return file_path
        
        logger.warning(f"在 {output_dir} 中找不到 .info.json 檔案")
        return None
    
    def _extract_youtube_info_from_json(self, info_json_path: Path) -> Optional[Dict[str, Any]]:
        """
        從 yt-dlp 生成的 .info.json 中提取 YouTube 資訊
        
        Args:
            info_json_path: .info.json 檔案路徑
            
        Returns:
            YouTube 資訊字典或 None
        """
        try:
            with info_json_path.open('r', encoding='utf-8') as f:
                info_data = json.load(f)
            
            # 提取關鍵的 YouTube 資訊
            youtube_info = {
                "video_id": info_data.get('id'),
                "title": info_data.get('title'),
                "description": info_data.get('description'),
                "uploader": info_data.get('uploader'),
                "uploader_id": info_data.get('uploader_id'),
                "upload_date": info_data.get('upload_date'),
                "duration": info_data.get('duration'),
                "view_count": info_data.get('view_count'),
                "like_count": info_data.get('like_count'),
                "original_url": info_data.get('original_url') or info_data.get('webpage_url'),
                "webpage_url": info_data.get('webpage_url'),
                "thumbnail": info_data.get('thumbnail'),
                "tags": info_data.get('tags', []),
                "categories": info_data.get('categories', []),
                "language": info_data.get('language'),
                "age_limit": info_data.get('age_limit'),
                "availability": info_data.get('availability')
            }
            
            logger.debug(f"從 .info.json 提取到資訊: {youtube_info['title']}")
            return youtube_info
            
        except (json.JSONDecodeError, IOError, KeyError) as e:
            logger.error(f"無法讀取或解析 .info.json 檔案 {info_json_path}: {e}")
            return None
    
    def _scan_downloaded_files_from_info_json(self, output_dir: Path, info_json_path: Path) -> Dict[str, Any]:
        """
        基於 yt-dlp 的 .info.json 精確掃描下載的檔案
        
        Args:
            output_dir: 輸出目錄
            info_json_path: .info.json 檔案路徑
            
        Returns:
            檔案資訊字典
        """
        downloaded_files = {
            "video": None,
            "audio_tracks": [],
            "subtitle_tracks": [],
            "thumbnail": None
        }
        
        try:
            with info_json_path.open('r', encoding='utf-8') as f:
                info_data = json.load(f)
            
            # 🔥 優化：從 .info.json 的 requested_downloads 精確獲取檔案資訊
            requested_downloads = info_data.get('requested_downloads', [])
            if requested_downloads:
                for download in requested_downloads:
                    filepath = download.get('filepath')
                    if filepath:
                        file_path = Path(filepath)
                        if file_path.exists():
                            file_size = file_path.stat().st_size
                            ext = download.get('ext', file_path.suffix[1:])
                            
                            # 判斷檔案類型
                            if download.get('vcodec') != 'none' and download.get('acodec') != 'none':
                                # 影片檔案（含音轨）
                                downloaded_files["video"] = {
                                    "path": file_path.name,
                                    "format": ext,
                                    "file_size_bytes": file_size,
                                    "resolution": f"{download.get('width', 0)}x{download.get('height', 0)}",
                                    "fps": download.get('fps'),
                                    "vcodec": download.get('vcodec'),
                                    "acodec": download.get('acodec')
                                }
                            elif download.get('acodec') != 'none':
                                # 純音轨檔案
                                downloaded_files["audio_tracks"].append({
                                    "language": download.get('language', 'unknown'),
                                    "path": file_path.name,
                                    "format": ext,
                                    "file_size_bytes": file_size,
                                    "acodec": download.get('acodec'),
                                    "abr": download.get('abr')
                                })
            
            # 從 .info.json 的 requested_subtitles 精確獲取字幕資訊
            requested_subtitles = info_data.get('requested_subtitles', {})
            for lang, subtitle_info in requested_subtitles.items():
                subtitle_path = subtitle_info.get('filepath')
                if subtitle_path:
                    sub_file = Path(subtitle_path)
                    if sub_file.exists():
                        downloaded_files["subtitle_tracks"].append({
                            "language": lang,
                            "path": sub_file.name,
                            "format": subtitle_info.get('ext', sub_file.suffix[1:]),
                            "auto_generated": False,  # requested_subtitles 通常不是自動生成
                            "file_size_bytes": sub_file.stat().st_size
                        })
            
            # 從 .info.json 的 automatic_captions 獲取自動字幕
            automatic_captions = info_data.get('automatic_captions', {})
            for lang, caption_list in automatic_captions.items():
                # 檢查是否有對應的檔案下載
                for caption_info in caption_list:
                    if caption_info.get('filepath'):
                        cap_file = Path(caption_info['filepath'])
                        if cap_file.exists():
                            downloaded_files["subtitle_tracks"].append({
                                "language": lang,
                                "path": cap_file.name,
                                "format": caption_info.get('ext', cap_file.suffix[1:]),
                                "auto_generated": True,
                                "file_size_bytes": cap_file.stat().st_size
                            })
                            break  # 每種語言只取一個
            
            # 掃描目錄中的縮圖檔案
            for file_path in output_dir.iterdir():
                if file_path.is_file():
                    file_name = file_path.name.lower()
                    if any(ext in file_name for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                        downloaded_files["thumbnail"] = {
                            "path": file_path.name,
                            "format": file_path.suffix[1:],
                            "file_size_bytes": file_path.stat().st_size
                        }
                        break
            
            logger.debug(f"基於 .info.json 掃描到檔案: 影片={bool(downloaded_files['video'])}, "
                        f"音轨={len(downloaded_files['audio_tracks'])}, "
                        f"字幕={len(downloaded_files['subtitle_tracks'])}, "
                        f"縮圖={bool(downloaded_files['thumbnail'])}")
            
            return downloaded_files
            
        except (json.JSONDecodeError, IOError, KeyError) as e:
            logger.error(f"無法從 .info.json 掃描檔案: {e}")
            # 如果 .info.json 解析失敗，回退到舊的檔名掃描方式
            logger.info("回退到傳統檔名掃描方式")
            return self._scan_downloaded_files_legacy(output_dir)
    
    def _scan_downloaded_files_legacy(self, output_dir: Path) -> Dict[str, Any]:
        """
        傳統的檔名掃描方式（備用）
        
        Args:
            output_dir: 輸出目錄
            
        Returns:
            檔案資訊字典
        """
        logger.warning("使用傳統檔名掃描方式（可能不精確）")
        return self._scan_downloaded_files(output_dir, "unknown")
    
    def _scan_downloaded_files(self, output_dir: Path, video_id: str) -> Dict[str, Any]:
        """
        掃描下載目錄中的檔案
        
        Args:
            output_dir: 輸出目錄
            video_id: 影片 ID
            
        Returns:
            檔案資訊字典
        """
        downloaded_files = {
            "video": None,
            "audio_tracks": [],
            "subtitle_tracks": [],
            "thumbnail": None
        }
        
        if not output_dir.exists():
            return downloaded_files
        
        # 掃描所有檔案
        for file_path in output_dir.iterdir():
            if not file_path.is_file():
                continue
            
            file_name = file_path.name.lower()
            file_size = file_path.stat().st_size
            
            # 影片檔案
            if any(ext in file_name for ext in ['.mp4', '.mkv', '.webm']) and '.part' not in file_name:
                downloaded_files["video"] = {
                    "path": file_path.name,
                    "format": file_path.suffix[1:],  # 去掉點
                    "file_size_bytes": file_size
                }
            
            # 音軌檔案
            elif any(ext in file_name for ext in ['.m4a', '.mp3', '.wav']) and '.part' not in file_name:
                # 嘗試從檔名提取語言資訊
                lang = "unknown"
                if '.en.' in file_name or file_name.endswith('.en.m4a'):
                    lang = "en"
                elif '.zh.' in file_name:
                    lang = "zh"
                
                downloaded_files["audio_tracks"].append({
                    "language": lang,
                    "path": file_path.name,
                    "format": file_path.suffix[1:],
                    "file_size_bytes": file_size
                })
            
            # 字幕檔案
            elif any(ext in file_name for ext in ['.srt', '.vtt', '.ass']):
                # 提取語言資訊
                lang = "unknown"
                auto_generated = "auto" in file_name
                
                if '.en.' in file_name:
                    lang = "en"
                elif '.zh.' in file_name:
                    lang = "zh"
                
                downloaded_files["subtitle_tracks"].append({
                    "language": lang,
                    "path": file_path.name,
                    "format": file_path.suffix[1:],
                    "auto_generated": auto_generated,
                    "file_size_bytes": file_size
                })
            
            # 縮圖檔案
            elif any(ext in file_name for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                downloaded_files["thumbnail"] = {
                    "path": file_path.name,
                    "format": file_path.suffix[1:],
                    "file_size_bytes": file_size
                }
        
        logger.debug(f"掃描到檔案: 影片={bool(downloaded_files['video'])}, "
                    f"音軌={len(downloaded_files['audio_tracks'])}, "
                    f"字幕={len(downloaded_files['subtitle_tracks'])}, "
                    f"縮圖={bool(downloaded_files['thumbnail'])}")
        
        return downloaded_files
    
    def _create_video_info_json(self, youtube_info: Dict[str, Any], downloaded_files: Dict[str, Any], 
                               performance_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        建立符合 SDD v1.1 格式的 video_info.json
        
        Args:
            youtube_info: 從 .info.json 提取的完整 YouTube 資訊
            downloaded_files: 下載的檔案資訊
            performance_data: 效能數據
            
        Returns:
            video_info.json 內容
        """
        # 計算總檔案大小
        total_size = 0
        if downloaded_files["video"]:
            total_size += downloaded_files["video"]["file_size_bytes"]
        
        for audio in downloaded_files["audio_tracks"]:
            total_size += audio["file_size_bytes"]
        
        for subtitle in downloaded_files["subtitle_tracks"]:
            total_size += subtitle["file_size_bytes"]
        
        if downloaded_files["thumbnail"]:
            total_size += downloaded_files["thumbnail"]["file_size_bytes"]
        
        # 🔥 優化：使用從 .info.json 提取的完整 YouTube 資訊
        video_info = {
            "schema_version": "1.1",
            "youtube_info": youtube_info,  # 完整的 YouTube 資訊，不再是空百
            "downloaded_files": downloaded_files,
            "processing_status": {
                **performance_data,
                "total_size_bytes": total_size,
                "removed_from_playlist": False  # 會由主邏輯更新
            }
        }
        
        return video_info
    
    def get_progress_info(self) -> Dict[str, Any]:
        """
        獲取當前下載進度資訊
        
        Returns:
            進度資訊字典
        """
        return self.progress.to_dict()