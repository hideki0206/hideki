import requests
import json
import time
from config import THREADS_ACCESS_TOKEN, THREADS_USER_ID

THREADS_API_BASE = "https://graph.threads.net/v1.0"


def create_media_container(text: str) -> str:
    """投稿用メディアコンテナを作成"""
    resp = requests.post(
        f"{THREADS_API_BASE}/{THREADS_USER_ID}/threads",
        params={
            "media_type": "TEXT",
            "text": text,
            "access_token": THREADS_ACCESS_TOKEN,
        }
    )
    resp.raise_for_status()
    container_id = resp.json().get("id")
    print(f"コンテナ作成: {container_id}")
    return container_id


def publish_post(container_id: str) -> str:
    """メディアコンテナを公開"""
    time.sleep(30)  # Threads APIの推奨待機時間

    resp = requests.post(
        f"{THREADS_API_BASE}/{THREADS_USER_ID}/threads_publish",
        params={
            "creation_id": container_id,
            "access_token": THREADS_ACCESS_TOKEN,
        }
    )
    resp.raise_for_status()
    post_id = resp.json().get("id")
    print(f"投稿完了: {post_id}")
    return post_id


def post_to_threads(text: str) -> str:
    """Threadsに投稿"""
    container_id = create_media_container(text)
    post_id = publish_post(container_id)
    return post_id


if __name__ == "__main__":
    # テスト投稿
    test_text = "テスト投稿です #テスト"
    post_id = post_to_threads(test_text)
    print(f"投稿ID: {post_id}")
