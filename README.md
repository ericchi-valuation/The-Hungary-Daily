# Hungary-Daily-Insider
新聞來源：10/11 個來源正常（BBJ 直接 RSS 空集，已改用 Google News site search 替代）
Reddit：r/hungary 23 篇、r/budapest 24 篇，全部正常
下一步：設定 GitHub Secrets
您的 Repo ericchi-valuation/Hungary-Daily-Insider 需要在 Settings → Secrets → Actions 新增：

Secret 名稱	說明
GEMINI_API_KEY	同 TW 版，直接沿用
GMAIL_ADDRESS	同 TW 版，直接沿用
GMAIL_APP_PASSWORD	同 TW 版，直接沿用
THREADS_USER_ID	同 TW 版，直接沿用
THREADS_ACCESS_TOKEN	同 TW 版，直接沿用
FB_GROUP_ID	Hungary Expats Facebook Group 的數字 ID
FB_ACCESS_TOKEN	Meta Graph API 長效 Token（有才會抓 FB；沒填也不會崩潰）
⚠️ 冬夏令提醒：每年 10 月底匈牙利改回冬令時間（CET = UTC+1），需手動把 cron 改為 30 5 * * *；3 月底改回夏令再改回 30 4 * * *。

10
news_fetcher.py
social_fetcher.py
script_generator.py
main.py
daily_podcast.yml
rss_generator.py
content_reformatter.py
.env.example
audio_builder.py
test_reddit.py
我先不處理FB的ID以及token可以繼續進行嗎?


完全可以！我在 social_fetcher.py 裡已經寫好了 graceful fallback。只要 FB_GROUP_ID 和 FB_ACCESS_TOKEN 沒有設定，程式碼會自動跳過 Facebook，不會崩潰：

python
if not group_id or not access_token or access_token == "your_fb_access_token_here":
    print("⚠️  FB_GROUP_ID / FB_ACCESS_TOKEN not set – skipping Facebook source.")
    return []
pipeline 會正常跑完，只是社群段落只有 Reddit r/hungary + r/budapest 兩個來源（已經很夠用了）。

下一步：推送到 GitHub 並設定 Secrets
現在要把 Hungary 資料夾推到您的新 Repo。請問您的 Hungary 資料夾有沒有已經 git init 過？我可以幫您一鍵完成以下流程：

git init + 設定 remote 到 https://github.com/ericchi-valuation/Hungary-Daily-Insider
建立 .gitignore（排除 .env、__pycache__、*.mp3 等）
第一次 git push
或者，如果您想手動在 GitHub 上建立 Repo 再 clone 也可以告訴我，我來說明步驟。

請確認：GitHub 上的 Hungary-Daily-Insider Repo 已經建立了嗎？（空白的就好，不需要有任何初始檔案）

