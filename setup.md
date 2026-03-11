# セットアップ手順

## 1. GitHubリポジトリを作成

GitHubで新しいリポジトリを作成し、このフォルダをプッシュします。

```bash
cd /Applications/00_AI/threads-auto-post
git init
git add .
git commit -m "initial commit"
git remote add origin https://github.com/あなたのアカウント/threads-auto-post.git
git push -u origin main
```

## 2. GitHub Secretsを設定

GitHubリポジトリの Settings → Secrets and variables → Actions で以下を登録：

| Secret名 | 値 |
|---|---|
| `ANTHROPIC_API_KEY` | AnthropicのAPIキー |
| `CHATWORK_API_TOKEN` | ChatWorkのAPIトークン |
| `CHATWORK_ROOM_ID` | ChatWorkの個人チャットルームID |
| `THREADS_ACCESS_TOKEN` | Threads APIアクセストークン |
| `THREADS_USER_ID` | ThreadsのユーザーID |

## 3. ChatWork APIトークンの取得

ChatWork → 右上アイコン → サービス連携 → API → APIトークンを発行

## 4. ChatWorkルームIDの確認

ChatWorkの個人チャットを開き、URLの数字部分がルームIDです。
例: `https://www.chatwork.com/#!rid12345678` → `12345678`

## 5. Threads APIの設定

1. https://developers.facebook.com にアクセス
2. アプリを作成（タイプ: ビジネス）
3. Threads APIを追加
4. アクセストークンを取得

## 6. 動作確認

```bash
pip install -r requirements.txt
playwright install chromium

# 手動テスト
python main.py scrape
```

## 7. 競合アカウントの追加

`config.py` の `COMPETITOR_ACCOUNTS` に追加：
```python
COMPETITOR_ACCOUNTS = [
    "@salon.marketing",
    "@account2",  # ← 追加
    "@account3",  # ← 追加
]
```
