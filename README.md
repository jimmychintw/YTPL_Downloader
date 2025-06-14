# YTPL_Downloader

自動化 YouTube Playlist 下載工具，監控指定的 Playlist，自動下載新影片並從雲端移除。

## 環境需求

- Python 3.13+
- macOS
- yt-dlp

## 安裝步驟

1. 啟動虛擬環境：
   ```bash
   source venv/bin/activate
   ```

2. 安裝依賴：
   ```bash
   pip install -r requirements.txt
   ```

3. 安裝 yt-dlp：
   ```bash
   brew install yt-dlp
   # 或
   pip install yt-dlp
   ```

4. 設定 config.ini（從 config.ini.example 複製）

5. 設定 Google OAuth 2.0 認證

## 使用方式

```bash
./venv/bin/python src/main_downloader.py
```

## 專案結構

- `src/` - 原始碼目錄
  - `main_downloader.py` - 主程式入口
  - `config_parser.py` - 配置檔解析
  - `youtube_api_client.py` - YouTube API 客戶端
  - `video_downloader.py` - 影片下載模組
  - `file_manager.py` - 檔案管理模組
  - `logger.py` - 日誌模組