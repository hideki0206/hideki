import requests
import re
from config_freelance import CHATWORK_API_TOKEN, CHATWORK_ROOM_ID

BASE_URL = "https://api.chatwork.com/v2"
HEADERS = {"X-ChatWorkToken": CHATWORK_API_TOKEN}

SLOT_LABELS = {
    "morning": "朝",
    "noon": "昼",
    "evening": "夜",
}
SLOT_DISPLAY = {
    "morning": "🌅 朝（7:00）",
    "noon": "☀️ 昼（12:00）",
    "evening": "🌙 夜（19:00）",
}


def send_posts_for_approval(posts: list[dict]) -> str:
    """生成された投稿をChatWorkに送信して承認を求める（フリーランス用）"""
    lines = ["[投稿案・@hideki0206] 本日のThreads投稿です。\n各投稿ごとに返信してください。\n"]

    for i, post in enumerate(posts, 1):
        slot_label = SLOT_DISPLAY.get(post["time_slot"], post["time_slot"])
        jp_label = SLOT_LABELS.get(post["time_slot"], post["time_slot"])
        lines.append(f"━━━━━━━━━━━━━━━")
        lines.append(f"【{i}】{slot_label}")
        lines.append(f"テーマ: {post['theme']}")
        lines.append(f"\n{post['text']}\n")
        lines.append(f"→ 返信例：「{jp_label} 承認」または「{jp_label} 修正：〇〇」")

    lines.append("━━━━━━━━━━━━━━━")

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


def send_revised_post_for_approval(post: dict) -> str:
    """修正した1投稿をChatWorkに再提案"""
    jp_label = SLOT_LABELS.get(post["time_slot"], post["time_slot"])
    slot_display = SLOT_DISPLAY.get(post["time_slot"], post["time_slot"])

    message = (
        f"[修正案・@hideki0206] {slot_display} の修正案です。\n\n"
        f"テーマ: {post['theme']}\n\n"
        f"{post['text']}\n\n"
        f"→ 返信例：「{jp_label} 承認」または「{jp_label} 修正：〇〇」"
    )

    resp = requests.post(
        f"{BASE_URL}/rooms/{CHATWORK_ROOM_ID}/messages",
        headers=HEADERS,
        data={"body": message}
    )
    resp.raise_for_status()
    message_id = resp.json().get("message_id", "")
    print(f"修正案送信完了 (message_id: {message_id})")
    return message_id


def check_approvals(posts: list[dict]) -> list[dict]:
    """ChatWorkのメッセージを確認して承認/修正指示を返す"""
    resp = requests.get(
        f"{BASE_URL}/rooms/{CHATWORK_ROOM_ID}/messages",
        headers=HEADERS,
        params={"force": 1}
    )
    resp.raise_for_status()
    messages = resp.json()

    # スロットごとの最新ステータスを記録
    slot_status = {}  # slot -> {"status": "approved" | "revision", "note": "..."}

    for msg in messages:
        body = msg.get("body", "").strip()

        for slot, jp in SLOT_LABELS.items():
            # 「朝 承認」「昼 承認」「夜 承認」
            if re.match(rf'^{jp}\s*承認$', body):
                slot_status[slot] = {"status": "approved"}

            # 「朝 修正：〇〇」「昼 修正：〇〇」「夜 修正：〇〇」
            m = re.match(rf'^{jp}\s*修正[：:]\s*(.+)$', body, re.DOTALL)
            if m:
                slot_status[slot] = {"status": "revision", "note": m.group(1).strip()}

    result = []
    for post in posts:
        s = slot_status.get(post["time_slot"])
        if s:
            result.append({**post, **s})
        else:
            result.append({**post, "status": "pending"})

    return result


def send_post_result(time_slot: str, success: bool, text: str = ""):
    """投稿結果をChatWorkに通知"""
    slot_label = SLOT_LABELS.get(time_slot, time_slot)
    if success:
        message = f"✅ [@hideki0206] {slot_label}の投稿が完了しました！\n\n{text}"
    else:
        message = f"❌ [@hideki0206] {slot_label}の投稿に失敗しました。確認してください。"

    requests.post(
        f"{BASE_URL}/rooms/{CHATWORK_ROOM_ID}/messages",
        headers=HEADERS,
        data={"body": message}
    )
