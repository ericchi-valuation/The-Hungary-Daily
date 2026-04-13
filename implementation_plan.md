# Hungary Daily Insider Podcast — 實作計畫

## 背景說明

將台灣版 "Taiwan Daily Insider" 的自動化 Podcast 系統，改造為針對匈牙利的版本 **"Hungary Daily Insider"**。  
目標受眾：**居住在布達佩斯的外籍人士、外商主管、歐盟公務人員**（類比台灣版的外籍就業金卡持卡人）。

本計畫的改動集中在「本地化」三個核心環節：**新聞來源、社群話題來源、AI 編輯 System Prompt**。架構與 DevOps 流程（GitHub Actions、音訊混音、電子報、RSS Feed）基本不動。

---

## 需要您回答的問題

> [!IMPORTANT]
> **播客語言**：台灣版是英文廣播稿。匈牙利版也維持**英文**嗎？（針對外籍聽眾）

> [!IMPORTANT]
> **播出時間**：台灣版設定在每天早上 06:30 台灣時間（UTC 22:30）播出。匈牙利版建議改為 **07:00 布達佩斯時間（UTC 06:00，夏令時 UTC 05:00）**，您同意嗎？

> [!IMPORTANT]
> **社群論壇**：台灣版抓 PTT + Dcard。匈牙利版沒有等效的在地匿名論壇，建議改為抓 **Reddit r/hungary** 的熱門文章（via Reddit JSON API，無需帳號）。您同意這個替代方案嗎？

> [!IMPORTANT]
> **GitHub Repo**：這個項目最終會推送到哪個 GitHub Repository？名稱與 TW 版相同還是新開一個？（因為 RSS feed URL 和 Releases 連結都需要正確的 `github.repository`）

---

## 改動範圍

### 1. `fetchers/news_fetcher.py` — 新聞來源替換

**台灣版** 使用中央社、Yahoo 奇摩、工商時報、經濟日報等繁中來源。  
**匈牙利版** 改為以下英文新聞 RSS 來源：

| 來源名稱 | RSS Feed URL | 涵蓋內容 |
|---|---|---|
| Hungary Today | `https://hungarytoday.hu/feed` | 每日政治/社會綜合 |
| Daily News Hungary | `https://dailynewshungary.com/feed/` | 時事/地方新聞 |
| Budapest Business Journal | `https://bbj.hu/rss` | 商業/財經 |
| Google News – Hungary Economy | `https://news.google.com/rss/search?q=Hungary+economy+business&hl=en-HU&gl=HU&ceid=HU:en` | Google 精選商業財經 |
| Google News – Budapest | `https://news.google.com/rss/search?q=Budapest+news&hl=en-HU&gl=HU&ceid=HU:en` | 城市事件/時事 |
| The Budapest Times | `https://budapesttimes.hu/feed` | 人文/藝術/生活 |
| EU & Visegrád (Google News) | `https://news.google.com/rss/search?q=Hungary+EU+Orban+Visegrad&hl=en&gl=US&ceid=US:en` | 地緣政治/歐盟關係 |

**關鍵字過濾黑名單**也需更新：移除台灣八卦詞彙，改為英文常見垃圾新聞關鍵字（clickbait 型標題）。

---

### 2. `fetchers/social_fetcher.py` — 社群來源替換

移除 `get_ptt_trending()` 和 `get_dcard_trending_bypassed()`。  
新增以下兩個函式：

#### `get_reddit_hungary(limit)`
- 呼叫 `https://www.reddit.com/r/hungary/hot.json`（Reddit 公開的 JSON endpoint，不需 OAuth）
- 設定 `User-Agent: HungaryDailyInsiderBot/1.0`
- 抓取熱門文章的標題與連結

#### `get_reddit_budapest(limit)`
- 呼叫 `https://www.reddit.com/r/budapest/hot.json`
- 同上邏輯，聚焦布達佩斯城市生活話題

---

### 3. `core/script_generator.py` — AI System Prompt 本地化

將 System Prompt 從台灣版完整改寫為匈牙利版：

- **節目名稱**：`Hungary Daily Insider`
- **目標受眾**：`foreign professionals, expats, and EU citizens living/working in Budapest, Hungary`
- **替換地名語音訓練**：台灣地名 → 匈牙利地名
  - `Budapest` → `Boo-da-pesht`
  - `Debrecen` → `Debb-ret-sen`
  - `Miskolc` → `Mish-kolts`
  - `Győr` → `Djur`
  - `Pécs` → `Paych`
- **節目定位聚焦**：  
  - 歐盟-匈牙利政治張力（Orbán 政府、rule of law 爭議）
  - 布達佩斯商業生態與外商投資環境（德國車廠 BMW、Audi、電動車電池廠等重大投資）
  - 匈牙利福林（HUF）匯率動向
  - 社群話題結尾段改為 "Trending in Budapest" segment

---

### 4. `main.py` — 顯示文字與輸出檔名更新

| 項目 | 台灣版 | 匈牙利版 |
|---|---|---|
| 啟動訊息 | `AI Taiwan Daily Podcast 自動產製系統啟動` | `AI Hungary Daily Podcast Auto-Production System` |
| 輸出音檔 | `TaiwanDaily_Podcast.mp3` / `_Final.mp3` | `HungaryDaily_Podcast.mp3` / `_Final.mp3` |
| 電子報主旨 | `Taiwan Daily Insider - {date}` | `Hungary Daily Insider - {date}` |

---

### 5. `.github/workflows/daily_podcast.yml` — CI/CD 調整

| 項目 | 台灣版 | 匈牙利版 |
|---|---|---|
| Cron 時間 | `30 22 * * *`（UTC 22:30 = 台灣 06:30） | `00 05 * * *`（UTC 05:00 = 布達佩斯 07:00 夏令）|
| Release 標籤 | `ep-{TODAY}` + `TaiwanDaily_Podcast_Final.mp3` | `ep-{TODAY}` + `HungaryDaily_Podcast_Final.mp3` |
| RSS 生成標題 | `Taiwan Daily Insider - {TODAY}` | `Hungary Daily Insider - {TODAY}` |
| TZ 時區 | `Asia/Taipei` | `Europe/Budapest` |
| ffprobe 指向 | `TaiwanDaily_Podcast_Final.mp3` | `HungaryDaily_Podcast_Final.mp3` |

---

### 6. `core/rss_generator.py` —  Feed Metadata 更新

若有寫死的節目標題/描述，將其更新為 Hungary Daily Insider 的相關資訊（頻道名、描述、連結）。

---

### 7. `.env.example` — 說明文字更新（版本標示用）

小幅更新注解，確認與 Hungary 版本相符，無功能變動。

---

## 驗證計畫

### 本地測試
1. 執行 `python fetchers/news_fetcher.py` 確認 7 個來源均可成功抓到文章
2. 執行 `python fetchers/social_fetcher.py` 確認 Reddit r/hungary + r/budapest 可正常返回資料
3. 執行 `python main.py` 完整跑一遍，檢查 `script.txt` 內容符合匈牙利視角

### GitHub Actions
4. 推送至 GitHub 後，手動點「Run workflow」測試一次完整自動化流程

