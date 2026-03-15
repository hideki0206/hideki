import requests
import re
from datetime import timezone, timedelta
from config import CHATWORK_API_TOKEN, CHATWORK_ROOM_ID

JST = timezone(timedelta(hours=9))
BASE_URL = "https://api.chatwork.com/v2"
HEADERS = {"X-ChatWorkToken": CHATWORK_API_TOKEN}

SLOT_TAG = {
    "morning": "[朝]",
    "noon":    "[昼]",
    "evening": "[夜]",
}
SLOT_LABEL = {
    "morning": "🌅 朝（7:00）",
    "noon":    "☀️ 昼（12:00）",
    "evening": "🌙 夜（19:00）",
}
TAG_TO_SLOT = {v: k for k, v in SLOT_TAG.items()}


def send_posts_for_approval(posts: list[dict]):
    """投稿ごとに個別メッセージでChatWorkに送信して承認を求める"""
    for post in posts:
        slot = post["time_slot"]
        tag = SLOT_TAG.get(slot, f"[{slot}]")
        label = SLOT_LABEL.get(slot, slot)

        lines = [f"[To:909701] 【投稿案】{label}"]
        lines.append(f"テーマ: {post['theme']}")
        lines.append("")

        if post.get("is_thread") and post.get("thread_parts"):
            parts = post["thread_parts"]
            for j, part in enumerate(parts, 1):
                lines.append(f"--- {j}/{len(parts)} ---")
                lines.append(part)
                lines.append("")
        else:
            lines.append(post.get("text", ""))
            lines.append("")

        lines.append("─────────────")
        lines.append(f"▶ 承認する場合：")
        lines.append(f"  {tag} 承認")
        lines.append(f"▶ 修正する場合：")
        lines.append(f"  {tag} 修正")
        lines.append(f"  （修正後の全文をこの下に書いてください）")
        if post.get("is_thread"):
            lines.append(f"  ※ ツリー投稿の場合は「--- 1/6 ---」の形式で各パートを区切ってください")

        resp = requests.post(
            f"{BASE_URL}/rooms/{CHATWORK_ROOM_ID}/messages",
            headers=HEADERS,
            data={"body": "\n".join(lines)}
        )
        resp.raise_for_status()
        msg_id = resp.json().get("message_id", "")
        print(f"ChatWork送信完了 [{slot}] (message_id: {msg_id})")


def check_approvals(posts: list[dict]) -> list[dict]:
    """ChatWorkのメッセージを確認して承認/修正済み投稿を返す"""
    resp = requests.get(
        f"{BASE_URL}/rooms/{CHATWORK_ROOM_ID}/messages",
        headers=HEADERS,
        params={"force": 1}
    )
    resp.raise_for_status()
    messages = resp.json()

    # slot -> {"status": "approved"} or {"status": "modified", "content": "..."}
    decisions = {}

    for msg in messages:
        body = msg.get("body", "").strip()

        for tag, slot in TAG_TO_SLOT.items():
            # 承認パターン: "[朝] 承認" or "[朝]承認"
            if re.match(rf'^{re.escape(tag)}\s*承認', body):
                decisions[slot] = {"status": "approved"}

            # 修正パターン: "[朝] 修正\n<内容>"
            elif re.match(rf'^{re.escape(tag)}\s*修正', body):
                content = re.sub(rf'^{re.escape(tag)}\s*修正\s*', '', body).strip()
                decisions[slot] = {"status": "modified", "content": content}

    approved_posts = []
    for post in posts:
        slot = post["time_slot"]
        decision = decisions.get(slot)
        if not decision:
            continue

        if decision["status"] == "approved":
            approved_posts.append({**post, "status": "approved"})

        elif decision["status"] == "modified":
            content = decision["content"]
            modified = {**post, "status": "approved"}

            if post.get("is_thread"):
                # "--- 1/6 ---\n本文\n--- 2/6 ---\n本文..." をパース
                parts = re.split(r'---\s*\d+/\d+\s*---', content)
                parts = [p.strip() for p in parts if p.strip()]
                if parts:
                    modified["thread_parts"] = parts
            else:
                modified["text"] = content

            approved_posts.append(modified)

    return approved_posts


def send_post_result(time_slot: str, success: bool, text: str = ""):
    """投稿結果をChatWorkに通知"""
    label = SLOT_LABEL.get(time_slot, time_slot)
    if success:
        preview = text[:100] + "…" if len(text) > 100 else text
        message = f"✅ {label}の投稿が完了しました！\n\n{preview}"
    else:
        message = f"❌ {label}の投稿に失敗しました。確認してください。"

    requests.post(
        f"{BASE_URL}/rooms/{CHATWORK_ROOM_ID}/messages",
        headers=HEADERS,
        data={"body": message}
    )
