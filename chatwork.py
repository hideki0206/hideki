import requests
import re
from datetime import timezone, timedelta
from config import CHATWORK_API_TOKEN, CHATWORK_ROOM_ID

JST = timezone(timedelta(hours=9))
BASE_URL = "https://api.chatwork.com/v2"
HEADERS = {"X-ChatWorkToken": CHATWORK_API_TOKEN}

SLOT_LABEL = {
    "morning": "🌅 朝（7:00）",
    "noon":    "☀️ 昼（12:00）",
    "evening": "🌙 夜（19:00）",
}


def send_posts_for_approval(posts: list[dict]) -> dict:
    """投稿ごとに個別メッセージを送信し、message_id を返す"""
    message_ids = {}

    for post in posts:
        slot = post["time_slot"]
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
        lines.append("▶ このメッセージに返信してください")
        lines.append("  「承認」→ そのまま投稿")
        lines.append("  修正後の全文 → 修正内容で投稿")
        if post.get("is_thread"):
            lines.append("  ※ ツリー修正は「--- 1/6 ---」区切りで各パートを書いてください")

        resp = requests.post(
            f"{BASE_URL}/rooms/{CHATWORK_ROOM_ID}/messages",
            headers=HEADERS,
            data={"body": "\n".join(lines)}
        )
        resp.raise_for_status()
        msg_id = resp.json().get("message_id", "")
        message_ids[slot] = msg_id
        print(f"ChatWork送信完了 [{slot}] (message_id: {msg_id})")

    return message_ids


def check_approvals(posts: list[dict]) -> list[dict]:
    """ChatWorkの返信を確認して承認/修正済み投稿を返す"""
    resp = requests.get(
        f"{BASE_URL}/rooms/{CHATWORK_ROOM_ID}/messages",
        headers=HEADERS,
        params={"force": 1}
    )
    resp.raise_for_status()
    messages = resp.json()

    # message_id -> slot のマップを posts から構築
    id_to_slot = {}
    for post in posts:
        mid = post.get("chatwork_message_id")
        if mid:
            id_to_slot[str(mid)] = post["time_slot"]

    # slot -> decision
    decisions = {}

    for msg in messages:
        body = msg.get("body", "").strip()

        # ChatWorkの引用返信形式: [rp aid=xxx to=ROOMID-MESSAGEID]
        rp_match = re.search(r'\[rp\b[^\]]*\bto=\d+-(\d+)\]', body)
        if not rp_match:
            continue

        replied_to_id = rp_match.group(1)
        slot = id_to_slot.get(replied_to_id)
        if not slot:
            continue

        # 引用ブロック([qt]...[/qt])を除いた本文を取り出す
        clean = re.sub(r'\[qt\].*?\[/qt\]', '', body, flags=re.DOTALL)
        clean = re.sub(r'\[rp\b[^\]]*\]', '', clean).strip()

        if clean == "承認":
            decisions[slot] = {"status": "approved"}
        elif clean:
            decisions[slot] = {"status": "modified", "content": clean}

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
