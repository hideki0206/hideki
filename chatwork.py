import requests
import json
import re
from datetime import datetime, timezone, timedelta
from config import CHATWORK_API_TOKEN, CHATWORK_ROOM_ID

JST = timezone(timedelta(hours=9))
BASE_URL = "https://api.chatwork.com/v2"
HEADERS = {"X-ChatWorkToken": CHATWORK_API_TOKEN}


def send_posts_for_approval(posts: list[dict]) -> str:
    """生成された投稿をChatWorkに送信して承認を求める"""
    lines = ["[To:909701] [投稿案] 本日のThreads投稿です。各投稿に「承認」または「修正：〇〇」と返信してください。\n"]

    for i, post in enumerate(posts, 1):
        slot_label = {"morning": "🌅 朝（7:00）", "noon": "☀️ 昼（12:00）", "evening": "🌙 夜（19:00）"}.get(post["time_slot"], post["time_slot"])
        lines.append(f"━━━━━━━━━━━━━━━")
        lines.append(f"【{i}】{slot_label}")
        lines.append(f"テーマ: {post['theme']}")
        if post.get("is_thread") and post.get("thread_parts"):
            for j, part in enumerate(post["thread_parts"], 1):
                lines.append(f"\n--- {j}/{len(post['thread_parts'])} ---\n{part}")
        else:
            lines.append(f"\n{post.get('text', '')}\n")

    lines.append("━━━━━━━━━━━━━━━")
    lines.append("※ 「承認」→ そのまま投稿")
    lines.append("※ 「修正：〇〇」→ 修正して再提案")

    message = "\n".join(lines)

    resp = requests.post(
        f"{BASE_URL}/rooms/{CHATWORK_ROOM_ID}/messages",
        headers=HEADERS,
        data={"body": message}
    )
    resp.raise_for_status()
    message_id = resp.json().get("message_id", "")
    print(f"ChatWork送信完了 (message_id: {message_id})")
    return message_id


def check_approvals(posts: list[dict]) -> list[dict]:
    """ChatWorkのメッセージを確認して承認済み投稿を返す"""
    resp = requests.get(
        f"{BASE_URL}/rooms/{CHATWORK_ROOM_ID}/messages",
        headers=HEADERS,
        params={"force": 1}
    )
    resp.raise_for_status()
    messages = resp.json()

    approved_slots = set()
    revision_requests = {}

    for msg in messages:
        body = msg.get("body", "").strip()
        if body == "承認":
            # 直近3スロット全て承認
            approved_slots = {"morning", "noon", "evening", "thread"}
        elif body.startswith("修正：") or body.startswith("修正:"):
            note = re.sub(r'^修正[：:]', '', body).strip()
            # どのスロットへの修正かは簡易的にメッセージ順で判定
            revision_requests["all"] = note

    approved_posts = []
    for post in posts:
        if post["time_slot"] in approved_slots:
            approved_posts.append({**post, "status": "approved"})
        elif "all" in revision_requests:
            approved_posts.append({**post, "status": "revision", "note": revision_requests["all"]})

    return approved_posts


def send_post_result(time_slot: str, success: bool, text: str = ""):
    """投稿結果をChatWorkに通知"""
    slot_label = {"morning": "朝", "noon": "昼", "evening": "夜", "thread": "夜(ツリー)"}.get(time_slot, time_slot)
    if success:
        message = f"✅ {slot_label}の投稿が完了しました！\n\n{text}"
    else:
        message = f"❌ {slot_label}の投稿に失敗しました。確認してください。"

    requests.post(
        f"{BASE_URL}/rooms/{CHATWORK_ROOM_ID}/messages",
        headers=HEADERS,
        data={"body": message}
    )


if __name__ == "__main__":
    # テスト
    test_posts = [
        {"time_slot": "morning", "text": "朝のテスト投稿です", "theme": "テスト"},
        {"time_slot": "noon", "text": "昼のテスト投稿です", "theme": "テスト"},
        {"time_slot": "evening", "text": "夜のテスト投稿です", "theme": "テスト"},
    ]
    send_posts_for_approval(test_posts)
