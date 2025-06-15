

------

# **系統設計文件 (SDD)：YTPL_Downloader v1.2**

## **版本歷史**

- v1.0 (2024-01-10): 初始版本
- v1.1 (2024-01-13): 新增斷點續傳實作細節、檔案命名規則、OAuth Desktop Flow、效能監控設計
- v1.2 (2025-06-15): 修正影片下載格式以獲取最高解析度，並整合了雙通道日誌記錄與純文字摘要報告功能。

## **1. 整體架構與組件**

YTPL_Downloader 專案被設計為一個獨立的 Python 應用程式，專注於高效自動化地下載 YouTube Playlist 中的影片內容。其內部結構旨在實現模組化、清晰的職責劃分和高可維護性。

### **1.1 專案目錄結構**

```
my_projects_workspace/
└── YTPL_Downloader/
    ├── src/
    │   ├── main_downloader.py
    │   ├── config_parser.py
    │   ├── youtube_api_client.py
    │   ├── video_downloader.py
    │   ├── file_manager.py
    │   └── logger.py
    ├── logs/                     # <-- (v1.2 新增) 存放日誌檔案
    ├── config.ini
    ├── requirements.txt
    ├── README.md
    └── venv/
```

### **1.2 主要程式模組與職責**

1. **main_downloader.py (主入口點 & 協調者) (v1.2 更新)**
   - **職責**：專案的核心協調器。負責程式的啟動、初始化日誌系統、讀取配置檔、初始化 YouTube API 客戶端、協調遍歷所有監控的 Playlist，並對每個 Playlist 中的影片執行檢查、下載、儲存和移除流程。處理核心錯誤和重試邏輯，並在成功處理影片後，將其本地路徑印到標準輸出。 **在執行過程中收集統計數據（成功、失敗、跳過數量），並在程式結束時呼叫自身的一個私有輔助函數來格式化並打印純文字的執行摘要報告。**
   - **依賴**：config_parser, youtube_api_client, video_downloader, file_manager, logger。
2. **config_parser.py (設定檔解析器)**
   - **職責**：專門負責讀取和解析 config.ini 檔案。將 INI 格式的數據轉換為 Python 程式易於操作的資料結構。
   - **依賴**：configparser (Python 內建)。
3. **youtube_api_client.py (YouTube API 客戶端)**
   - **職責**：封裝所有與 YouTube Data API 交互的邏輯。包括執行 OAuth 2.0 認證流程（獲取和刷新 token）、執行 playlistItems.list API 查詢 Playlist 內容，以及執行 playlistItems.delete API 從 Playlist 中移除影片。
   - **依賴**：google-api-python-client, google-auth-oauthlib, google-auth-httplib2。
4. **video_downloader.py (影片下載器)**
   - **職責**：負責實際執行影片、音軌、字幕和縮圖的下載工作。它將作為一個輕量級的包裝器，呼叫外部工具 yt-dlp 來完成核心下載任務，並捕獲 yt-dlp 的輸出。支援斷點續傳功能，確保大檔案下載的可靠性。
   - **依賴**：subprocess (Python 內建)。
5. **file_manager.py (檔案管理器)**
   - **職責**：負責所有與本地檔案系統交互的操作。包括在指定目錄中創建影片子資料夾、將下載內容儲存到正確的位置、讀取和寫入 video_info.json 檔案、以及掃描現有下載目錄以識別已處理的影片 ID。
   - **依賴**：os, shutil (Python 內建), json (Python 內建)。
6. **logger.py (日誌模組) (v1.2 更新)**
   - **職責**：提供一個統一且可配置的日誌記錄接口。 **修改其設定，使其能同時將日誌輸出到標準輸出 (console) 和一個位於 `logs/` 目錄下、以時間戳命名的日誌檔案。**
   - **依賴**：logging (Python 內建)。

## **2. 技術選型**

YTPL_Downloader 的技術棧優先選擇 Python 標準庫，並輔以少量經過驗證的第三方庫，以確保專案的輕量級、穩定性和易於維護性。

- Python 環境管理

  ：

  - **技術**：**Python 虛擬環境 (venv)**。
  - **用途**：隔離專案依賴，避免衝突。

- 配置檔解析

  ：

  - **技術**：**Python 內建 configparser 模組**。
  - **用途**：讀取和解析 config.ini 檔案。

- YouTube Data API 交互 (認證與操作)

  ：

  - **技術**：**google-api-python-client**, **google-auth-oauthlib**, **google-auth-httplib2**。
  - **用途**：處理 OAuth 2.0 桌面應用程式認證流程，執行 YouTube Data API 的 playlistItems.list 和 playlistItems.delete 操作。

- 影片、音軌、字幕下載與縮圖獲取

  ：

  - **技術**：**yt-dlp (命令行工具)**，通過 **Python 內建 subprocess 模組**呼叫。
  - **用途**：作為核心下載引擎，獲取各種媒體資源和元數據。

- JSON 數據操作

  ：

  - **技術**：**Python 內建 json 模組**。
  - **用途**：讀取和寫入 video_info.json 檔案。

- 檔案系統操作

  ：

  - **技術**：**Python 內建 os 和 shutil 模組**。
  - **用途**：處理路徑、創建目錄、讀寫文件、管理文件結構。

- 日誌記錄

  ：

  - **技術**：**Python 內建 logging 模組**。
  - **用途**：提供靈活的日誌輸出管理。

## **3. 核心流程設計**

YTPL_Downloader 將作為一個由外部排程器（如 macOS 的 launchd）定時觸發執行的獨立程式。每次啟動，它將執行一次完整的監控和處理循環，然後正常退出。

### **3.1 啟動與初始化**

1. **日誌系統初始化 (v1.2 更新)**：呼叫 `logger.py` 中的設定函數。此函數會根據當前時間創建一個新的日誌檔案（例如 `logs/ytpl_downloader_2025-06-15_15-21-38.log`），並設定好同時向該檔案和控制台輸出的雙通道日誌記錄器。

2. 讀取配置檔 (config.ini)

   ：

   - 呼叫 config_parser.py 讀取並解析 config.ini。
   - 處理 [General] 區塊和所有 [Playlist_&lt;DescriptiveName>] 區塊。
   - **錯誤處理**：配置檔缺失或格式錯誤將導致程式終止。

3. YouTube API 客戶端初始化與 OAuth 2.0 認證

   ：

   - 呼叫 youtube_api_client.py，使用 client_secrets_file 和 token_storage_file 進行初始化。
   - **OAuth 2.0 Desktop Application Flow**：使用 `google-auth-oauthlib` 的 `InstalledAppFlow` 進行桌面應用程式認證。
   - **Token 管理**：每次 API 呼叫前檢查 token 有效性，並自動使用 refresh token 更新過期的 access token。
   - **首次認證**：如果 token_storage_file 不存在或無效，自動啟動認證流程。

4. **日誌記錄成功啟動訊息**。

### **3.2 主監控與處理循環**

1. **遍歷所有已配置的 Playlist**：程式將根據 config.ini 中定義的順序，逐一處理每個 Playlist 區塊。
2. **單個 Playlist 處理**：對於每個 Playlist，執行 **3.3 Playlist 處理邏輯**。

### **3.3 Playlist 處理邏輯**

對於每個 Playlist：

1. **獲取雲端 Playlist 影片列表**：使用 youtube_api_client.py 查詢 YouTube Data API，獲取指定 Playlist 的所有影片 ID。
2. **讀取本地已下載影片列表**：file_manager.py 掃描該 Playlist 對應的 download_directory，讀取每個子資料夾內的 video_info.json，提取 video_id，構建本地已下載影片 ID 集合。
3. **識別新影片**：比對雲端 Playlist 影片 ID 列表與本地已下載影片 ID 集合，將不在本地列表中的影片識別為「新影片」。
4. **處理每個新影片**：對於每個識別出的新影片 ID，執行 **3.4 影片處理流程**。

### **3.4 影片處理流程**

對於每個新影片：

1. 創建本地影片子資料夾

   ：file_manager.py 在 Playlist 的 download_directory 下創建新的獨立子資料夾。

   - **命名規則**：格式為 `[YYYY-MM-DD]_[sanitized_title]_[video_id]`。

2. 下載影片所有內容 (v1.2 修訂)

   ：

   - ```
     video_downloader.py
     ```

      呼叫 

     ```
     yt-dlp
     ```

      命令。參數包括：

     - **`--format "bestvideo\*+bestaudio/best"`**：明確指定下載最高品質的視訊和音訊流並合併。
     - **`--merge-output-format mp4`**：合併時統一輸出為 mp4 格式。
     - YouTube URL
     - 目標子資料夾
     - `--continue`：啟用斷點續傳。
     - `--no-overwrites`：避免覆寫已存在的檔案。
     - `--write-info-json`：輸出元數據。
     - 下載所有音軌、所有字幕、縮圖。

3. **儲存 video_info.json**：yt-dlp 已直接生成 video_info.json。程式可選擇性地驗證和補充內容。

4. **從雲端 Playlist 移除影片**：僅當所有下載步驟成功後，才呼叫 youtube_api_client.py 的 playlistItems.delete API 移除影片。

5. **輸出成功訊息**：如果影片成功處理，程式將在標準輸出 (stdout) 中清晰地印出該影片獨立子資料夾的絕對路徑。

### **3.5 錯誤處理與重試機制**

- **全局錯誤捕獲**：main_downloader.py 包含頂層 try-except 塊捕獲未預期異常。
- **特定錯誤處理**：配置檔錯誤、OAuth 認證錯誤導致啟動終止。API 請求失敗實施指數退避重試。
- **冪等性**：通過掃描本地 video_info.json 中的 video_id，確保不重複下載已完整處理的影片。

### **3.6 執行總結與報告 (v1.2 新增)**

1. **數據收集**：在 `main_downloader.py` 的主循環中，宣告一個簡單的字典或計數器物件（例如 `stats = {"success": 0, "failed": 0, "skipped": 0}`），用於在處理每個影片後累加計數。同時記錄程式開始時間。

2. 報告生成與顯示

   ：在 

   ```
   main_downloader.py
   ```

    的主 

   ```
   try...finally
   ```

    區塊的 

   ```
   finally
   ```

    部分，定義一個

   內部輔助函數

   （例如 

   ```
   _print_summary_report
   ```

   ）。此函數負責計算總耗時，並使用 f-string 格式化 

   ```
   stats
   ```

    字典中的數據，將純文字報告打印到標準輸出。

   - 報告範例

     ：

     Plaintext

     ```
     --- YTPL_Downloader Execution Summary ---
     Total Playlists Processed: 2
     New Videos Downloaded: 5
     Skipped (Already Exists): 12
     Failed Downloads: 1
     Total Execution Time: 5m 10s
     Detailed log saved to: logs/ytpl_downloader_2025-06-15_15-21-38.log
     ---------------------------------------
     ```

## **4. 資料結構設計**

### **4.1 config.ini 檔案結構**

Ini, TOML

```
; 這是一個 config.ini 範例檔案

[General]
; OAuth 2.0 客戶端密鑰檔案的路徑，從 Google Cloud Console 下載的 JSON 檔案。
client_secrets_file = /path/to/your/client_secrets.json

; 儲存用戶 OAuth 2.0 token 的檔案路徑。此檔案由 YTPL_Downloader 自動生成和管理。
token_storage_file = /path/to/your/token.json

; YTPL_Downloader 內部在處理完所有 Playlist 後，會等待的時間（秒）。
check_interval_seconds = 60

[Playlist_MyFavoriteTechVideos]
; 要監控的 YouTube Playlist 的完整 URL。
playlist_url = https://www.youtube.com/playlist?list=PLxxxxxxxxxxxxxx

; 該 Playlist 下載內容的絕對根儲存目錄路徑。
download_directory = /Users/youruser/Downloads/YTPL_Videos/TechVideos

[Playlist_KidsStoryTime]
playlist_url = https://www.youtube.com/playlist?list=PLyyyyyyyyyyyyyy
download_directory = /Users/youruser/Downloads/YTPL_Videos/KidsStories

; ... 可以添加更多 [Playlist_YourCustomName] 區塊
```

### **4.2 video_info.json 檔案結構**

檔名：video_info.json

預期位置：[download_directory]/[video_id_or_formatted_title]/video_info.json

JSON

```
{
  "schema_version": "1.1",
  "youtube_info": {
    "video_id": "dQw4w9WgXcQ",
    "title": "Never Gonna Give You Up",
    "description": "Rick Astley - Never Gonna Give You Up (Official Music Video)",
    "uploader": "RickAstley",
    "channel_id": "UCuAxFwQY5fGzB535B5h7R1g",
    "publish_date": "1987-07-27",
    "original_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "duration_seconds": 213,
    "views": 1000000000,
    "category": "Music",
    "tags": ["pop", "80s", "music video"]
  },
  "downloaded_files": {
    "video": {
      "path": "video.mp4",
      "format": "mp4",
      "resolution": "1920x1080",
      "file_size_bytes": 157286400
    },
    "audio_tracks": [
      {
        "language": "en",
        "path": "audio_en.mp3",
        "format": "mp3",
        "codec": "mp3",
        "file_size_bytes": 8388608
      }
    ],
    "subtitle_tracks": [
      {
        "language": "en",
        "path": "subtitle_en.srt",
        "format": "srt",
        "auto_generated": true,
        "file_size_bytes": 32768
      }
    ],
    "thumbnail": {
      "path": "thumbnail.jpg",
      "format": "jpg",
      "file_size_bytes": 204800
    }
  },
  "processing_status": {
    "download_timestamp": "2023-10-27T10:30:00Z",
    "download_start_time": "2023-10-27T10:25:00Z",
    "download_duration_seconds": 300,
    "download_status": "completed",
    "retry_count": 0,
    "total_size_bytes": 165879808,
    "average_speed_mbps": 4.42,
    "playlist_origin": "https://www.youtube.com/playlist?list=PLxxxxxxxxxxxxxx",
    "removed_from_playlist": true
  }
}
```

## **5. 部署考量 (macOS)**

YTPL_Downloader 被設計為透過 macOS 的 launchd 服務來自動定時運行。

- **虛擬環境 (venv) 整合**：程式應在一個獨立的 Python 虛擬環境 (venv) 中安裝所有依賴。launchd 的 .plist 檔案將直接指定虛擬環境內的 Python 解釋器絕對路徑來運行 main_downloader.py。

- launchd 配置

  ：

  - **.plist 檔案位置**：`~/Library/LaunchAgents/` 目錄下。
  - **ProgramArguments**：必須精確指向虛擬環境內 Python 解釋器的絕對路徑，以及 main_downloader.py 的絕對路徑。
  - **StartInterval**：設定為程式期望的運行頻率。
  - **StandardOutPath / StandardErrorPath**：配置為將程式的所有日誌和錯誤輸出重定向到指定的日誌檔案。
  - **WorkingDirectory**：設定為 YTPL_Downloader 專案的根目錄。