"""
YouTube API 客戶端模組 - 處理與 YouTube Data API 的所有交互

功能：
- OAuth 2.0 Desktop Application Flow 認證
- Token 管理和自動刷新
- Playlist 內容查詢
- 從 Playlist 移除影片
"""

import json
import os
import stat
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, parse_qs

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from logger import get_logger

logger = get_logger('youtube_api_client')


class YouTubeAPIClient:
    """YouTube API 客戶端 - 處理所有 YouTube Data API 操作"""
    
    # YouTube Data API 的權限範圍
    SCOPES = [
        'https://www.googleapis.com/auth/youtube.readonly',  # 讀取 playlist
        'https://www.googleapis.com/auth/youtube'  # 修改 playlist（移除影片）
    ]
    
    def __init__(self, client_secrets_file: str, token_storage_file: str):
        """
        初始化 YouTube API 客戶端
        
        Args:
            client_secrets_file: Google OAuth 2.0 客戶端密鑰檔案路徑
            token_storage_file: Token 儲存檔案路徑
        """
        self.client_secrets_file = client_secrets_file
        self.token_storage_file = token_storage_file
        self.credentials: Optional[Credentials] = None
        self.service = None
        
        # 驗證 client_secrets 檔案
        if not Path(client_secrets_file).exists():
            raise FileNotFoundError(f"找不到 client_secrets 檔案: {client_secrets_file}")
        
        logger.info(f"初始化 YouTube API 客戶端")
        logger.debug(f"Client secrets: {client_secrets_file}")
        logger.debug(f"Token storage: {token_storage_file}")
    
    def _load_credentials(self) -> Optional[Credentials]:
        """
        載入已儲存的認證憑證
        
        Returns:
            認證憑證或 None
        """
        token_path = Path(self.token_storage_file)
        
        if not token_path.exists():
            logger.debug("Token 檔案不存在")
            return None
        
        try:
            with token_path.open('r', encoding='utf-8') as f:
                token_data = json.load(f)
            
            credentials = Credentials.from_authorized_user_info(token_data, self.SCOPES)
            logger.debug("成功載入已儲存的認證憑證")
            return credentials
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"無法載入 token 檔案 {token_path}: {e}")
            return None
    
    def _save_credentials(self, credentials: Credentials) -> None:
        """
        儲存認證憑證到檔案
        
        Args:
            credentials: 要儲存的認證憑證
        """
        token_path = Path(self.token_storage_file)
        
        # 確保目錄存在
        token_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # 建立 token 資料
            token_data = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes
            }
            
            # 寫入檔案
            with token_path.open('w', encoding='utf-8') as f:
                json.dump(token_data, f, indent=2)
            
            # 設定檔案權限為 600（僅擁有者可讀寫）
            token_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
            
            logger.info(f"認證憑證已儲存到: {token_path}")
            
        except (OSError, IOError) as e:
            logger.error(f"無法儲存 token 檔案 {token_path}: {e}")
            raise
    
    def _refresh_credentials(self, credentials: Credentials) -> bool:
        """
        刷新過期的認證憑證
        
        Args:
            credentials: 要刷新的認證憑證
            
        Returns:
            是否成功刷新
        """
        try:
            credentials.refresh(Request())
            logger.info("認證憑證已成功刷新")
            self._save_credentials(credentials)
            return True
        except Exception as e:
            logger.error(f"無法刷新認證憑證: {e}")
            return False
    
    def _perform_oauth_flow(self) -> Optional[Credentials]:
        """
        執行 OAuth 2.0 Desktop Application Flow 認證
        
        Returns:
            認證憑證或 None
        """
        try:
            # 建立 OAuth flow
            flow = InstalledAppFlow.from_client_secrets_file(
                self.client_secrets_file, self.SCOPES
            )
            
            # 嘗試不同的 port 進行本地伺服器認證
            ports_to_try = [8080, 8081, 8082, 8083, 8084, 8085, 8086, 8087, 8088, 8089, 8090]
            
            for port in ports_to_try:
                try:
                    logger.info(f"嘗試在 port {port} 啟動 OAuth 認證流程")
                    
                    # 執行本地伺服器流程
                    credentials = flow.run_local_server(
                        port=port,
                        prompt='select_account',  # 允許選擇 Google 帳戶
                        success_message='認證成功！您現在可以關閉此視窗。',
                        open_browser=True
                    )
                    
                    logger.info(f"OAuth 認證成功（port {port}）")
                    return credentials
                    
                except OSError as e:
                    if "Address already in use" in str(e) or "已經在使用" in str(e):
                        logger.debug(f"Port {port} 被佔用，嘗試下一個 port")
                        continue
                    else:
                        logger.error(f"在 port {port} 啟動認證時發生錯誤: {e}")
                        continue
            
            # 如果所有 port 都失敗，嘗試手動認證方式
            logger.warning("所有 port 都被佔用，使用手動認證方式")
            return self._perform_manual_oauth_flow(flow)
            
        except Exception as e:
            logger.error(f"OAuth 認證流程失敗: {e}")
            return None
    
    def _perform_manual_oauth_flow(self, flow: InstalledAppFlow) -> Optional[Credentials]:
        """
        執行手動 OAuth 認證流程（當自動開啟瀏覽器失敗時）
        
        Args:
            flow: OAuth flow 物件
            
        Returns:
            認證憑證或 None
        """
        try:
            # 生成認證 URL
            auth_url, _ = flow.authorization_url(prompt='select_account')
            
            print("\n" + "="*60)
            print("需要手動認證")
            print("="*60)
            print(f"請開啟以下 URL 進行認證：")
            print(f"\n{auth_url}\n")
            print("完成認證後，請將重定向 URL 中的 'code' 參數值貼上：")
            
            # 讓使用者手動輸入授權碼
            auth_code = input("請輸入授權碼: ").strip()
            
            if not auth_code:
                logger.error("未提供授權碼")
                return None
            
            # 使用授權碼獲取憑證
            flow.fetch_token(code=auth_code)
            logger.info("手動 OAuth 認證成功")
            
            return flow.credentials
            
        except Exception as e:
            logger.error(f"手動 OAuth 認證失敗: {e}")
            return None
    
    def authenticate(self) -> bool:
        """
        執行完整的認證流程
        
        Returns:
            是否認證成功
        """
        logger.info("開始認證流程")
        
        # 1. 嘗試載入已儲存的憑證
        self.credentials = self._load_credentials()
        
        # 2. 檢查憑證是否有效
        if self.credentials:
            if self.credentials.valid:
                logger.info("使用已儲存的有效認證憑證")
            elif self.credentials.expired and self.credentials.refresh_token:
                logger.info("認證憑證已過期，嘗試刷新")
                if self._refresh_credentials(self.credentials):
                    logger.info("認證憑證刷新成功")
                else:
                    logger.warning("認證憑證刷新失敗，需要重新認證")
                    self.credentials = None
            else:
                logger.warning("認證憑證無效，需要重新認證")
                self.credentials = None
        
        # 3. 如果沒有有效憑證，執行 OAuth 流程
        if not self.credentials:
            logger.info("執行 OAuth 2.0 認證流程")
            self.credentials = self._perform_oauth_flow()
            
            if self.credentials:
                self._save_credentials(self.credentials)
                logger.info("新的認證憑證已儲存")
            else:
                logger.error("OAuth 認證失敗")
                return False
        
        # 4. 建立 YouTube API 服務
        try:
            self.service = build('youtube', 'v3', credentials=self.credentials)
            logger.info("YouTube API 服務建立成功")
            return True
        except Exception as e:
            logger.error(f"無法建立 YouTube API 服務: {e}")
            return False
    
    def extract_playlist_id(self, playlist_url: str) -> Optional[str]:
        """
        從 YouTube Playlist URL 中提取 playlist ID
        
        Args:
            playlist_url: YouTube Playlist URL
            
        Returns:
            Playlist ID 或 None
        """
        try:
            parsed_url = urlparse(playlist_url)
            query_params = parse_qs(parsed_url.query)
            
            if 'list' in query_params:
                playlist_id = query_params['list'][0]
                logger.debug(f"提取 playlist ID: {playlist_id}")
                return playlist_id
            else:
                logger.error(f"URL 中找不到 'list' 參數: {playlist_url}")
                return None
                
        except Exception as e:
            logger.error(f"無法解析 playlist URL {playlist_url}: {e}")
            return None
    
    def get_playlist_videos(self, playlist_url: str) -> List[Dict[str, Any]]:
        """
        獲取 Playlist 中所有影片的資訊
        
        Args:
            playlist_url: YouTube Playlist URL
            
        Returns:
            影片資訊列表，每個元素包含 video_id 和其他元數據
        """
        if not self.service:
            logger.error("YouTube API 服務未初始化，請先執行認證")
            return []
        
        playlist_id = self.extract_playlist_id(playlist_url)
        if not playlist_id:
            return []
        
        logger.info(f"獲取 playlist 影片列表: {playlist_id}")
        videos = []
        next_page_token = None
        
        try:
            while True:
                # 呼叫 playlistItems.list API
                request = self.service.playlistItems().list(
                    part='snippet,contentDetails',
                    playlistId=playlist_id,
                    maxResults=50,  # 每次最多獲取 50 個項目
                    pageToken=next_page_token
                )
                
                response = request.execute()
                
                # 處理回應中的每個項目
                for item in response.get('items', []):
                    snippet = item.get('snippet', {})
                    content_details = item.get('contentDetails', {})
                    
                    video_info = {
                        'playlist_item_id': item.get('id'),  # 用於刪除操作
                        'video_id': content_details.get('videoId'),
                        'title': snippet.get('title'),
                        'description': snippet.get('description'),
                        'published_at': snippet.get('publishedAt'),
                        'channel_title': snippet.get('videoOwnerChannelTitle'),
                        'position': snippet.get('position')
                    }
                    
                    # 過濾掉被刪除或私人的影片
                    if video_info['video_id'] and video_info['title'] != 'Deleted video':
                        videos.append(video_info)
                        logger.debug(f"找到影片: {video_info['video_id']} - {video_info['title']}")
                    else:
                        logger.debug(f"跳過無效影片: {item.get('id')}")
                
                # 檢查是否還有更多頁面
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break
            
            logger.info(f"獲取完成，共找到 {len(videos)} 個有效影片")
            return videos
            
        except HttpError as e:
            logger.error(f"YouTube API 錯誤: {e}")
            return []
        except Exception as e:
            logger.error(f"獲取 playlist 影片時發生錯誤: {e}")
            return []
    
    def remove_video_from_playlist(self, playlist_item_id: str) -> bool:
        """
        從 Playlist 中移除指定的項目（高效版本）
        
        Args:
            playlist_item_id: 要移除的 playlist item ID
            
        Returns:
            是否成功移除
            
        Note:
            這個函式只負責執行刪除操作，不負責查找 playlist_item_id。
            調用者應該事先通過 get_playlist_videos() 獲取完整列表，
            然後從中找到對應的 playlist_item_id。
            這樣可以避免重複的 API 調用，大幅提升效能。
        """
        if not self.service:
            logger.error("YouTube API 服務未初始化，請先執行認證")
            return False
        
        if not playlist_item_id:
            logger.error("playlist_item_id 不能為空")
            return False
        
        logger.info(f"從 playlist 移除項目: {playlist_item_id}")
        
        try:
            # 直接使用 playlistItems.delete API 移除項目
            request = self.service.playlistItems().delete(
                id=playlist_item_id
            )
            
            request.execute()
            logger.info(f"成功移除項目: {playlist_item_id}")
            return True
            
        except HttpError as e:
            error_content = e.content.decode('utf-8') if hasattr(e, 'content') else str(e)
            logger.error(f"移除項目時 YouTube API 錯誤: {error_content}")
            return False
        except Exception as e:
            logger.error(f"移除項目時發生錯誤: {e}")
            return False
    
    def remove_video_from_playlist_by_video_id(self, playlist_url: str, video_id: str) -> bool:
        """
        從 Playlist 中移除指定的影片（便利方法，效能較低）
        
        Args:
            playlist_url: YouTube Playlist URL
            video_id: 要移除的影片 ID
            
        Returns:
            是否成功移除
            
        Warning:
            此方法會重新獲取整個 playlist 來查找 playlist_item_id，
            效能較低，僅建議在單次移除時使用。
            批量操作請使用 remove_video_from_playlist() 配合事先獲取的列表。
        """
        if not self.service:
            logger.error("YouTube API 服務未初始化，請先執行認證")
            return False
        
        playlist_id = self.extract_playlist_id(playlist_url)
        if not playlist_id:
            return False
        
        logger.info(f"從 playlist {playlist_id} 移除影片: {video_id}")
        logger.warning("使用低效能方法移除影片，建議批量操作時使用 remove_video_from_playlist()")
        
        try:
            # 獲取 playlist 找到 playlist_item_id
            videos = self.get_playlist_videos(playlist_url)
            
            playlist_item_id = None
            for video in videos:
                if video['video_id'] == video_id:
                    playlist_item_id = video['playlist_item_id']
                    break
            
            if not playlist_item_id:
                logger.warning(f"在 playlist 中找不到影片 {video_id}")
                return False
            
            # 使用高效方法執行刪除
            return self.remove_video_from_playlist(playlist_item_id)
            
        except Exception as e:
            logger.error(f"移除影片時發生錯誤: {e}")
            return False
    
    def get_video_ids_from_playlist(self, playlist_url: str) -> List[str]:
        """
        獲取 Playlist 中所有影片的 ID 列表（簡化版本）
        
        Args:
            playlist_url: YouTube Playlist URL
            
        Returns:
            影片 ID 列表
        """
        videos = self.get_playlist_videos(playlist_url)
        video_ids = [video['video_id'] for video in videos if video['video_id']]
        
        logger.info(f"從 playlist 提取到 {len(video_ids)} 個影片 ID")
        return video_ids
    
    def create_video_id_to_item_id_mapping(self, playlist_url: str) -> Dict[str, str]:
        """
        建立 video_id 到 playlist_item_id 的映射（高效批量處理用）
        
        Args:
            playlist_url: YouTube Playlist URL
            
        Returns:
            字典：{video_id: playlist_item_id}
            
        Usage:
            # 高效的批量移除流程：
            mapping = client.create_video_id_to_item_id_mapping(playlist_url)
            for video_id in videos_to_remove:
                if video_id in mapping:
                    client.remove_video_from_playlist(mapping[video_id])
        """
        videos = self.get_playlist_videos(playlist_url)
        mapping = {
            video['video_id']: video['playlist_item_id'] 
            for video in videos 
            if video['video_id'] and video['playlist_item_id']
        }
        
        logger.info(f"建立映射完成，包含 {len(mapping)} 個 video_id -> playlist_item_id 對應")
        return mapping