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


def _build_post_body(post: dict, header: str) -> str:
    """投稿内容のメッセージ本文を組み立てる"""
    slot = post["time_slot"]
    label = SLOT_LABEL.get(slot, slot)
    lines = [f"[To:909701] {header}{label}"]
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

    slot = post["time_slot"]
    tag = {"morning": "[朝]", "noon": "[昼]", "evening": "[夜]"}.get(slot, f"[{slot}]")
    lines.append("─────────────")
    lines.append("▶ 返信ボタンで返信 または このルームにメッセージを送信：")
    lines.append(f"  承認 → 「{tag} 承認」")
    lines.append(f"  修正依頼 → 「{tag} 修正: ◯◯にして」")
    lines.append(f"  全文修正 → 「{tag} 全文」の後に修正後の全文")
    if post.get("is_thread"):
        lines.append("  ※ 全文修正は「--- 1/6 ---」区切りで各パートを書いてください")

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


def send_revision_proposal(post: dict) -> str:
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


def _apply_decision(decisions: dict, slot: str, clean: str):
    """承認/修正フィードバック/全文修正を decisions に登録"""
    if clean == "承認":
        decisions[slot] = {"status": "approved"}
    elif re.match(r'^修正[：:]\s*\S', clean):
        note = re.sub(r'^修正[：:]\s*', '', clean).strip()
        decisions[slot] = {"status": "feedback", "note": note}
    elif re.match(r'^全文', clean):
        content = re.sub(r'^全文\s*', '', clean).strip()
        if content:
            decisions[slot] = {"status": "modified", "content": content}
    elif clean:
        decisions[slot] = {"status": "modified", "content": clean}


def check_approvals(posts: list[dict]) -> list[dict]:
    """ChatWorkの返信を確認して承認/修正済み/フィードバック投稿を返す"""
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

    TAG_TO_SLOT = {"[朝]": "morning", "[昼]": "noon", "[夜]": "evening"}
    decisions = {}

    for msg in messages:
        body = msg.get("body", "").strip()

        # ── 方式1: 引用返信 [rp aid=xxx to=ROOMID-MESSAGEID] ──
        rp_match = re.search(r'\[rp\b[^\]]*\bto=\d+-(\d+)\]', body)
        if rp_match:
            slot = id_to_slot.get(rp_match.group(1))
            if slot:
                clean = re.sub(r'\[qt\].*?\[/qt\]', '', body, flags=re.DOTALL)
                clean = re.sub(r'\[rp\b[^\]]*\]', '', clean).strip()
                _apply_decision(decisions, slot, clean)
                continue

        # ── 方式2: タグ方式 "[朝] 承認" / "[朝] 修正: ..." / "[朝] 全文\n..." ──
        for tag, slot in TAG_TO_SLOT.items():
            if body.startswith(tag):
                clean = body[len(tag):].strip()
                _apply_decision(decisions, slot, clean)
                break

    approved_posts = []
    for post in posts:
        slot = post["time_slot"]
        decision = decisions.get(slot)
        if not decision:
            continue

        if decision["status"] == "approved":
            approved_posts.append({**post, "status": "approved"})

        elif decision["status"] == "feedback":
            approved_posts.append({**post, "status": "feedback",
                                   "feedback_note": decision["note"]})

        elif decision["status"] == "modified":
            content = decision["content"]
            modified = {**post, "status": "approved"}
            if post.get("is_thread"):
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
