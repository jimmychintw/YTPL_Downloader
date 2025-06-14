# YTPL_Downloader

🚀 **自動化 YouTube Playlist 下載工具** - 智能監控、完整下載、自動移除

## ✨ 專案特色

- **🎯 智能增量下載**：只下載新增的影片，避免重複
- **📺 完整內容下載**：最高畫質影片 + 所有字幕 + 縮圖
- **🔄 斷點續傳支援**：大檔案下載中斷後可續傳
- **🗑️ 自動雲端清理**：下載完成後自動從 Playlist 移除
- **📊 詳細進度監控**：實時追踪下載進度和效能數據
- **🛡️ 健壯錯誤處理**：優雅降級機制，確保系統穩定
- **🏗️ 模組化架構**：高內聚低耦合，易於維護擴展

## 🏗️ 系統架構

```
YTPL_Downloader/
├── src/
│   ├── logger.py              # 彩色日誌系統
│   ├── config_parser.py       # TOML 配置解析
│   ├── file_manager.py        # 檔案系統管理
│   ├── youtube_api_client.py  # YouTube Data API v3 客戶端
│   ├── video_downloader.py    # yt-dlp 下載器包裝
│   └── main_downloader.py     # 核心統籌模組
├── test_*.py                  # 完整測試套件
├── config.ini                 # 配置檔案範例
├── requirements.txt           # Python 依賴
└── CLAUDE.md                  # 開發指南
```

## 🚀 快速開始

### 1. 環境需求

- Python 3.13+
- yt-dlp (自動安裝)
- YouTube Data API v3 憑證

### 2. 安裝依賴

```bash
# 建立虛擬環境
python -m venv venv
source venv/bin/activate  # macOS/Linux
# 或 venv\Scripts\activate  # Windows

# 安裝依賴
pip install -r requirements.txt
```

### 3. 設定 YouTube API

1. 前往 [Google Cloud Console](https://console.cloud.google.com/)
2. 建立新專案或選擇現有專案
3. 啟用 YouTube Data API v3
4. 建立 OAuth 2.0 憑證（Desktop Application）
5. 下載 `client_secrets.json` 到專案根目錄

### 4. 配置設定

複製並編輯配置檔案：

```bash
cp config.ini.example config.ini
```

編輯 `config.ini`：

```ini
[General]
client_secrets_file = client_secrets.json
token_storage_file = token.json
check_interval_seconds = 3600

[Playlist_MyPlaylist]
playlist_url = https://www.youtube.com/playlist?list=YOUR_PLAYLIST_ID
download_directory = /path/to/download/folder
```

### 5. 執行程式

```bash
# 單次執行
python src/main_downloader.py

# 或直接執行主模組
python -m src.main_downloader
```

## 📋 功能特性

### 🎯 智能下載管理

- **增量更新**：比對本地與雲端差異，只下載新影片
- **自動分類**：每個影片建立獨立資料夾
- **完整備份**：影片、音軌、字幕、縮圖、元數據

### 🔧 技術亮點

- **單一事實來源**：使用 yt-dlp 的 `.info.json` 精確解析檔案資訊
- **零冗餘 API**：「一次獲取，多次使用」避免重複請求
- **優雅降級**：主要流程失敗時自動降級到備用方案
- **精細異常處理**：詳細錯誤分類，便於維護監控

### 📊 進度監控

```
2025-06-14 12:34:56 - 📥 獲取 Playlist 影片列表: MyPlaylist
2025-06-14 12:34:57 - 🔍 掃描本地已下載影片...
2025-06-14 12:34:58 - 🆕 發現 3 個新影片需要下載
2025-06-14 12:34:59 - 📺 處理影片 (1/3): Amazing Video Title
2025-06-14 12:35:30 - ✅ 下載成功: Amazing Video Title
2025-06-14 12:35:31 - 🗑️ 已從 Playlist 移除: Amazing Video Title
```

## 📁 輸出結構

```
download_folder/
├── video_id_1_title/
│   ├── video_file.mp4
│   ├── video_file.en.vtt      # 英文字幕
│   ├── video_file.zh.srt      # 中文字幕
│   ├── thumbnail.jpg
│   ├── video_file.info.json   # yt-dlp 元數據
│   └── video_info.json        # 標準化影片資訊
└── video_id_2_title/
    └── ...
```

## 🧪 測試

執行完整測試套件：

```bash
# 所有模組測試
python test_config_parser.py
python test_video_downloader.py
python test_main_downloader.py

# 或使用 pytest（如果安裝）
pytest test_*.py -v
```

## 🔒 安全性

- **OAuth 2.0 認證**：安全的 YouTube API 存取
- **權限最小化**：僅請求必要的 API 權限
- **本地儲存**：所有資料存放在本地，無雲端風險
- **敏感資訊保護**：token 檔案設定適當權限 (600)

## 🐛 故障排除

### 常見問題

1. **認證失敗**
   - 檢查 `client_secrets.json` 是否正確
   - 確認 YouTube Data API v3 已啟用
   - 檢查網路連線

2. **下載失敗**
   - 更新 yt-dlp：`pip install -U yt-dlp`
   - 檢查影片是否為私人或地區限制
   - 確認磁碟空間充足

3. **配置錯誤**
   - 驗證 config.ini 格式
   - 檢查 Playlist URL 是否正確
   - 確認下載目錄權限

### 除錯模式

啟用詳細日誌：

```python
from logger import setup_logger
setup_logger(level='DEBUG')
```

## 🤝 貢獻指南

1. Fork 專案
2. 建立功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交變更 (`git commit -m 'Add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 建立 Pull Request

## 📄 授權條款

本專案採用 MIT 授權條款。

## 🙏 致謝

- **yt-dlp**：優秀的影片下載工具
- **YouTube Data API**：官方 API 支援
- **Google OAuth**：安全認證機制

---

**🌟 如果這個專案對你有幫助，請給一個 Star！**