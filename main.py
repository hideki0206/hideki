"""
メインスクリプト
使い方:
  python main.py scrape        # スクレイピング＋投稿生成＋ChatWork通知
  python main.py post morning  # 朝のツリー投稿を実行
  python main.py post noon     # 昼のツリー投稿を実行
  python main.py post evening  # 夜のツリー投稿を実行
"""

import asyncio
import json
import sys
from pathlib import Path

POSTS_FILE = "generated_posts.json"


def cmd_scrape():
    from scraper import scrape_all_accounts, scrape_by_keyword, save_results
    from analyzer import analyze_and_generate, save_generated_posts
    from chatwork import send_posts_for_approval
    from config import ALL_ACCOUNTS, SCRAPE_POST_LIMIT, SEARCH_KEYWORDS

    print("=== スクレイピング開始 ===")
    results = asyncio.run(scrape_all_accounts(ALL_ACCOUNTS, SCRAPE_POST_LIMIT))

    print("\n=== キーワード検索（反応の良い投稿）===")
    keyword_posts = []
    for kw in SEARCH_KEYWORDS:
        print(f"検索中: {kw}")
        posts = asyncio.run(scrape_by_keyword(kw, limit=10))
        keyword_posts.extend(posts)
        print(f"  → {len(posts)}件取得")
    results["__keyword_search__"] = keyword_posts

    save_results(results, "scraped_posts.json")

    print("\n=== 投稿生成開始 ===")
    posts = analyze_and_generate(results)
    save_generated_posts(posts, POSTS_FILE)

    print("\n=== ChatWork通知 ===")
    message_ids = send_posts_for_approval(posts)

    # message_id を各投稿に保存（check_approvals の引用返信照合に使用）
    for post in posts:
        slot = post["time_slot"]
        if slot in message_ids:
            post["chatwork_message_id"] = message_ids[slot]
    save_generated_posts(posts, POSTS_FILE)

    print("完了！ChatWorkで承認してください。")


def cmd_post(time_slot: str):
    from chatwork import check_approvals, send_post_result
    from poster import post_to_threads, post_thread_to_threads

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

    # フィードバック（修正依頼）の場合はAIが修正案を生成してChatWorkに再送
    if approved_slot.get("status") == "feedback":
        from analyzer import revise_post
        from chatwork import send_revision_proposal
        note = approved_slot.get("feedback_note", "")
        print(f"=== {time_slot} 修正案生成中（依頼: {note}）===")
        revised = revise_post(approved_slot, note)
        new_msg_id = send_revision_proposal(revised)
        for i, post in enumerate(posts):
            if post["time_slot"] == time_slot:
                posts[i] = {**revised, "chatwork_message_id": new_msg_id}
        with open(POSTS_FILE, "w", encoding="utf-8") as f:
            json.dump(posts, f, ensure_ascii=False, indent=2)
        print(f"修正案をChatWorkに送信しました。承認後にワークフローを再実行してください。")
        return

    print(f"=== {time_slot} 投稿開始 ===")
    try:
        if approved_slot.get("is_thread") and approved_slot.get("thread_parts"):
            post_id = post_thread_to_threads(approved_slot["thread_parts"])
            preview = approved_slot["thread_parts"][0]
        else:
            post_id = post_to_threads(approved_slot["text"])
            preview = approved_slot["text"]
        send_post_result(time_slot, True, preview)
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
