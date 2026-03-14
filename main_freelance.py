"""
フリーランス向けThreads自動投稿（@hideki0206）
使い方:
  python main_freelance.py scrape        # スクレイピング＋投稿生成＋ChatWork通知
  python main_freelance.py post morning  # 朝の投稿を実行
  python main_freelance.py post noon     # 昼の投稿を実行
  python main_freelance.py post evening  # 夜の投稿を実行
"""

import asyncio
import json
import sys
from pathlib import Path

POSTS_FILE = "generated_posts_freelance.json"


def cmd_scrape():
    from scraper import scrape_all_accounts, scrape_by_keyword, save_results
    from analyzer_freelance import analyze_and_generate, save_generated_posts
    from chatwork_freelance import send_posts_for_approval
    from config_freelance import ALL_ACCOUNTS, SCRAPE_POST_LIMIT, SEARCH_KEYWORDS

    print("=== スクレイピング開始（フリーランス） ===")
    results = asyncio.run(scrape_all_accounts(ALL_ACCOUNTS, SCRAPE_POST_LIMIT))

    print("\n=== キーワード検索（反応の良い投稿）===")
    keyword_posts = []
    for kw in SEARCH_KEYWORDS:
        print(f"検索中: {kw}")
        posts = asyncio.run(scrape_by_keyword(kw, limit=10))
        keyword_posts.extend(posts)
        print(f"  → {len(posts)}件取得")
    results["__keyword_search__"] = keyword_posts

    save_results(results, "scraped_posts_freelance.json")

    print("\n=== 投稿生成開始 ===")
    posts = analyze_and_generate(results)
    save_generated_posts(posts, POSTS_FILE)

    print("\n=== ChatWork通知 ===")
    send_posts_for_approval(posts)
    print("完了！ChatWorkで承認してください。")


def cmd_post(time_slot: str):
    from chatwork_freelance import check_approvals, send_post_result
    from poster_freelance import post_to_threads

    if not Path(POSTS_FILE).exists():
        print(f"エラー: {POSTS_FILE} が見つかりません。先に scrape を実行してください。")
        sys.exit(1)

    with open(POSTS_FILE, encoding="utf-8") as f:
        posts = json.load(f)

    target = next((p for p in posts if p["time_slot"] == time_slot), None)
    if not target:
        print(f"エラー: {time_slot} の投稿が見つかりません。")
        sys.exit(1)

    approved = check_approvals(posts)
    approved_slot = next(
        (p for p in approved if p["time_slot"] == time_slot and p.get("status") == "approved"),
        None
    )

    if not approved_slot:
        print(f"{time_slot} はまだ承認されていません。スキップします。")
        return

    print(f"=== {time_slot} 投稿開始（@hideki0206）===")
    try:
        post_text = f"{approved_slot['theme']}\n\n{approved_slot['text']}"
        post_id = post_to_threads(post_text)
        send_post_result(time_slot, True, post_text)
        print(f"投稿完了: {post_id}")
    except Exception as e:
        send_post_result(time_slot, False)
        print(f"投稿失敗: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]
    if command == "scrape":
        cmd_scrape()
    elif command == "post" and len(sys.argv) >= 3:
        cmd_post(sys.argv[2])
    else:
        print(__doc__)
        sys.exit(1)
