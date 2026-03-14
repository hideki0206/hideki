import asyncio
import json
import base64
import os
from playwright.async_api import async_playwright
from config import THREADS_USERNAME, THREADS_PASSWORD

THREADS_SESSION = os.environ.get("THREADS_SESSION", "")


async def post_to_threads_async(text: str) -> str:
    """PlaywrightでThreadsにログインして投稿"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # セッションCookieがあれば使用
        if THREADS_SESSION:
            print("保存済みセッションを使用します")
            storage = json.loads(base64.b64decode(THREADS_SESSION).decode())
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
                storage_state=storage,
            )
        else:
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
            )

        page = await context.new_page()

        try:
            # セッションがあればホームへ直接アクセス、なければログイン
            if THREADS_SESSION:
                print("ホームにアクセス中...")
                await page.goto("https://www.threads.com", wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(3000)
                print(f"URL: {page.url}")
            else:
                print("Threadsにアクセス中...")
                await page.goto("https://www.threads.com/login", wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(3000)

                username_input = await page.wait_for_selector('input[type="text"]', timeout=15000)
                await username_input.fill(THREADS_USERNAME)
                password_input = await page.wait_for_selector('input[type="password"]', timeout=10000)
                await password_input.fill(THREADS_PASSWORD)

                login_btn = None
                for sel in ['button[type="submit"]', 'div[role="button"]:has-text("Log in")', 'div[role="button"]:has-text("ログイン")']:
                    try:
                        login_btn = await page.wait_for_selector(sel, timeout=3000)
                        if login_btn:
                            await login_btn.click()
                            break
                    except Exception:
                        continue

                if not login_btn:
                    await password_input.press("Enter")

                await page.wait_for_timeout(8000)
                print(f"ログイン後URL: {page.url}")

            # 投稿ボタンを探す
            print("投稿ボタンを探しています...")
            new_post_btn = None
            post_btn_selectors = [
                '[aria-label="New post"]',
                '[aria-label="新しいスレッドを作成"]',
                '[aria-label="Create"]',
                'a[href="/create"]',
            ]
            for sel in post_btn_selectors:
                try:
                    new_post_btn = await page.wait_for_selector(sel, timeout=5000)
                    if new_post_btn:
                        print(f"投稿ボタン発見: {sel}")
                        break
                except Exception:
                    continue

            if not new_post_btn:
                # ホームに移動して再試行
                await page.goto("https://www.threads.com", wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(3000)
                for sel in post_btn_selectors:
                    try:
                        new_post_btn = await page.wait_for_selector(sel, timeout=3000)
                        if new_post_btn:
                            print(f"ホームで投稿ボタン発見: {sel}")
                            break
                    except Exception:
                        continue

            if not new_post_btn:
                raise Exception("投稿ボタンが見つかりませんでした")

            await new_post_btn.click()
            await page.wait_for_timeout(2000)

            # テキスト入力
            print("テキストを入力中...")
            text_area = await page.wait_for_selector('[contenteditable="true"]', timeout=10000)
            await text_area.click()
            await text_area.fill(text)
            await page.wait_for_timeout(1000)

            # 投稿ボタン
            print("投稿ボタンを押しています...")
            submit_selectors = [
                '[data-testid="tray-button-post"]',
                'button:has-text("Post")',
                'button:has-text("投稿")',
                'div[role="button"]:has-text("Post")',
                'div[role="button"]:has-text("投稿")',
            ]
            submit_btn = None
            for sel in submit_selectors:
                try:
                    submit_btn = await page.wait_for_selector(sel, timeout=3000)
                    if submit_btn:
                        print(f"送信ボタン発見: {sel}")
                        break
                except Exception:
                    continue

            if not submit_btn:
                raise Exception("送信ボタンが見つかりませんでした")

            # オーバーレイに遮られる場合はJavaScriptでクリック
            await page.evaluate("el => el.click()", submit_btn)
            await page.wait_for_timeout(5000)
            print("投稿完了")
            return "posted"

        finally:
            await browser.close()


def post_to_threads(text: str) -> str:
    return asyncio.run(post_to_threads_async(text))


if __name__ == "__main__":
    test_text = "テスト投稿です #テスト"
    post_id = post_to_threads(test_text)
    print(f"結果: {post_id}")
