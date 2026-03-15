import requests
import re
from config_freelance import CHATWORK_API_TOKEN, CHATWORK_ROOM_ID

BASE_URL = "https://api.chatwork.com/v2"
HEADERS = {"X-ChatWorkToken": CHATWORK_API_TOKEN}

SLOT_LABEL = {
    "morning": "🌅 朝（7:00）",
    "noon":    "☀️ 昼（12:00）",
    "evening": "🌙 夜（19:00）",
}


def _build_post_body(post: dict, header: str) -> str:
    """投稿内容のメッセージ本文を組み立てる"""
    slot = post["time_slot"]
    label = SLOT_LABEL.get(slot, slot)
    lines = [f"[投稿案・@hideki0206] {header}{label}"]
    lines.append(f"テーマ: {post['theme']}")
    lines.append("")
    lines.append(post.get("text", ""))
    lines.append("")
    lines.append("─────────────")
    lines.append("▶ このメッセージに返信してください")
    lines.append("  「承認」→ そのまま投稿")
    lines.append("  「修正: ◯◯にして」→ AIが修正案を再提案")
    return "\n".join(lines)


def send_posts_for_approval(posts: list[dict]) -> dict:
    """投稿ごとに個別メッセージを送信し、message_id を返す"""
    message_ids = {}
    for post in posts:
        body = _build_post_body(post, "【投稿案】")
        resp = requests.post(
            f"{BASE_URL}/rooms/{CHATWORK_ROOM_ID}/messages",
            headers=HEADERS,
            data={"body": body}
        )
        resp.raise_for_status()
        msg_id = resp.json().get("message_id", "")
        message_ids[post["time_slot"]] = msg_id
        print(f"ChatWork送信完了 [{post['time_slot']}] (message_id: {msg_id})")
    return message_ids


def send_revised_post_for_approval(post: dict) -> str:
    """修正案を ChatWork に送信し、message_id を返す"""
    body = _build_post_body(post, "【修正案】")
    resp = requests.post(
        f"{BASE_URL}/rooms/{CHATWORK_ROOM_ID}/messages",
        headers=HEADERS,
        data={"body": body}
    )
    resp.raise_for_status()
    msg_id = resp.json().get("message_id", "")
    print(f"修正案送信完了 [{post['time_slot']}] (message_id: {msg_id})")
    return msg_id


def check_approvals(posts: list[dict]) -> list[dict]:
    """ChatWorkの返信を確認して承認/修正指示を返す"""
    resp = requests.get(
        f"{BASE_URL}/rooms/{CHATWORK_ROOM_ID}/messages",
        headers=HEADERS,
        params={"force": 1}
    )
    resp.raise_for_status()
    messages = resp.json()

    # message_id -> slot のマップ
    id_to_slot = {str(p["chatwork_message_id"]): p["time_slot"]
                  for p in posts if p.get("chatwork_message_id")}

    decisions = {}

    for msg in messages:
        body = msg.get("body", "").strip()

        # 引用返信形式: [rp aid=xxx to=ROOMID-MESSAGEID]
        rp_match = re.search(r'\[rp\b[^\]]*\bto=\d+-(\d+)\]', body)
        if not rp_match:
            continue

        slot = id_to_slot.get(rp_match.group(1))
        if not slot:
            continue

        # 引用ブロックと [rp] タグを除いた本文
        clean = re.sub(r'\[qt\].*?\[/qt\]', '', body, flags=re.DOTALL)
        clean = re.sub(r'\[rp\b[^\]]*\]', '', clean).strip()

        if clean == "承認":
            decisions[slot] = {"status": "approved"}
        elif re.match(r'^修正[：:]\s*\S', clean):
            note = re.sub(r'^修正[：:]\s*', '', clean).strip()
            decisions[slot] = {"status": "revision", "note": note}

    result = []
    for post in posts:
        slot = post["time_slot"]
        decision = decisions.get(slot)
        if decision:
            result.append({**post, **decision})
        else:
            result.append({**post, "status": "pending"})

    return result


def send_post_result(time_slot: str, success: bool, text: str = ""):
    """投稿結果をChatWorkに通知"""
    label = SLOT_LABEL.get(time_slot, time_slot)
    if success:
        preview = text[:100] + "…" if len(text) > 100 else text
        message = f"✅ [@hideki0206] {label}の投稿が完了しました！\n\n{preview}"
    else:
        message = f"❌ [@hideki0206] {label}の投稿に失敗しました。確認してください。"

    requests.post(
        f"{BASE_URL}/rooms/{CHATWORK_ROOM_ID}/messages",
        headers=HEADERS,
        data={"body": message}
    )
