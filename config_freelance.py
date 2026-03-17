import os

# hideki0206のThreadsアカウント
MY_ACCOUNT = "@hideki0206"

# 競合アカウント（後で追加可能）
COMPETITOR_ACCOUNTS = []

# 分析対象（自分のみ or 競合追加時）
ALL_ACCOUNTS = [MY_ACCOUNT] + COMPETITOR_ACCOUNTS

# 投稿スケジュール（JST）
POST_TIMES = {
    "morning": "07:00",
    "noon": "08:00",
    "evening": "19:00",
}

# ChatWork
CHATWORK_API_TOKEN = os.environ.get("CHATWORK_API_TOKEN", "")
CHATWORK_ROOM_ID = os.environ.get("CHATWORK_ROOM_ID_2", os.environ.get("CHATWORK_ROOM_ID", ""))

# Claude API
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Threads ログイン情報（2つ目のアカウント用）
THREADS_USERNAME = os.environ.get("THREADS_USERNAME_2", "")
THREADS_PASSWORD = os.environ.get("THREADS_PASSWORD_2", "")

# スクレイピング設定
SCRAPE_POST_LIMIT = 20

# トレンド調査用キーワード
SEARCH_KEYWORDS = [
    "フリーランス 稼ぎ方",
    "働き方 自由",
    "副業 月収",
]

# LINE登録URL（投稿のCTAに使用）
LINE_URL = os.environ.get("LINE_URL", "")

# 反応が良かった過去投稿（プロンプトの参考用）
# ※ プロフィール誘導CTAの参考投稿を先頭に配置
REFERENCE_POSTS = [
    """僕が手に入れた暮らし
 ・朝6時に起きて散歩→読書
・月150万円くらい稼ぐ
・好きな時に温泉&サウナ
・畑仕事や趣味に没頭
・毎日、家族で奥さんの手料理
・家族の急な予定にも100％対応
・家族で1ヶ月以上の海外滞在
 僕は、「豊かな暮らし」を選びました。
"理想の暮らし"は、
自分を知ることから始まります。
 僕のライフスタイルに
興味ある人は僕のプロフィールを見てね。
 裏側を公開してるから☺️""",

    """僕が手に入れた働き方。
 ・週に3〜4日、午前中はカフェで仕事
・月150万円くらい稼ぐ
・ランチを食べる前に筋トレ
・子どもの体調や行事にも柔軟に対応
・午後はゆっくり仕事だったり畑、好きなこと
・家族でタイやニュージーランド、バリ島などに長期滞在
 バリバリ働くより、「人生を豊かにする働き方」を選んだ。
 "働き方"は、
競うものではなく、
人生を豊かにするものだと思う。
 僕の働き方に
興味ある人は僕のプロフィールを見てね。
 裏側を公開してるから☺️""",

    """・『集客』を追うな『信頼』を築け
・『答え』を探すな『問い』を立てろ
・『伝える』だけでなく『伝わる』を設計しろ
・『一時』の利益より『一生』の関係を選べ
・『競合』と比べるな『顧客』と向き合え
・『多くの人』より『必要な人』に届けろ
・『成果』に縛られるな『意味』に立ち返れ""",

    """「お客さんの悩み、どう解決しよう？」
って考えるようになってからの方が
紹介も増えて、結果的に売上が上がった。""",

    """・お金より価値提供を考えてる
・お客さんの悩みに本気で向き合ってる
・短期的な売上より長期的な信頼を選ぶ
・「どう売るか？」より「どう役立つか？」""",
]
