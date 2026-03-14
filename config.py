import os

# 自分のThreadsアカウント
MY_ACCOUNT = "@salon.marketing"

# 競合アカウント（後で追加可能）
COMPETITOR_ACCOUNTS = [
    # "@account2",  # 後で追加
    # "@account3",  # 後で追加
]

# 分析対象（自分＋競合）
ALL_ACCOUNTS = [MY_ACCOUNT] + COMPETITOR_ACCOUNTS

# 投稿スケジュール（JST）
POST_TIMES = {
    "morning": "07:00",
    "noon": "12:00",
    "evening": "19:00",
}

# ChatWork
CHATWORK_API_TOKEN = os.environ.get("CHATWORK_API_TOKEN", "")
CHATWORK_ROOM_ID = os.environ.get("CHATWORK_ROOM_ID", "")

# Claude API
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Threads ログイン情報
THREADS_USERNAME = os.environ.get("THREADS_USERNAME", "")
THREADS_PASSWORD = os.environ.get("THREADS_PASSWORD", "")

# スクレイピング設定
SCRAPE_POST_LIMIT = 20  # 1アカウントあたり取得する投稿数
