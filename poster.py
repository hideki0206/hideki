import asyncio
import json
import base64
import os
from playwright.async_api import async_playwright
from config import THREADS_USERNAME, THREADS_PASSWORD

THREADS_SESSION = os.environ.get("THREADS_SESSION", "")


async def _setup_page() -> tuple:
    """ブラウザ起動・ログイン・ホーム遷移を行いpageを返す"""
    p_instance = await async_playwright().__aenter__()
    browser = await p_instance.chromium.launch(headless=True)
    ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    if THREADS_SESSION:
        storage = json.loads(base64.b64decode(THREADS_SESSION).decode())
        context = await browser.new_context(user_agent=ua, viewport={"width": 1280, "height": 800}, storage_state=storage)
    else:
        context = await browser.new_context(user_agent=ua, viewport={"width": 1280, "height": 800})

    page = await context.new_page()

    if THREADS_SESSION:
        print("保存済みセッションを使用します")
        await page.goto("https://www.threads.com", wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(5000)
    else:
        print("Threadsにアクセス中...")
        await page.goto("https://www.threads.com/login", wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(5000)
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

    return p_instance, browser, page


async def _open_compose(page) -> None:
    """「今なにしてる？」をクリックして新規スレッドモーダルを開く"""
    # ページが完全にロードされるまで待つ
    try:
        trigger = await page.wait_for_selector('text="今なにしてる？"', timeout=10000)
        await trigger.click()
        print("「今なにしてる？」をクリックしてモーダルを開きました")
    except Exception:
        raise Exception("「今なにしてる？」が見つかりませんでした。ページの読み込みを確認してください。")
    # モーダルが開くまで待つ
    await page.wait_for_selector('[contenteditable="true"]', timeout=10000)


async def post_to_threads_async(text: str) -> str:
    """PlaywrightでThreadsにログインして単発投稿"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

        if THREADS_SESSION:
            storage = json.loads(base64.b64decode(THREADS_SESSION).decode())
            context = await browser.new_context(user_agent=ua, viewport={"width": 1280, "height": 800}, storage_state=storage)
        else:
            context = await browser.new_context(user_agent=ua, viewport={"width": 1280, "height": 800})

        page = await context.new_page()

        try:
            if THREADS_SESSION:
                await page.goto("https://www.threads.com", wait_until="networkidle", timeout=60000)
                await page.wait_for_timeout(3000)
            else:
                await page.goto("https://www.threads.com/login", wait_until="networkidle", timeout=60000)
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

            await _open_compose(page)

            print("テキストを入力中...")
            text_area = await page.wait_for_selector('[contenteditable="true"]', timeout=10000)
            await text_area.click()
            await page.wait_for_timeout(500)
            await page.keyboard.type(text)
            await page.wait_for_timeout(1000)

            print("投稿ボタンを押しています...")
            post_btn = page.get_by_text("投稿", exact=True)
            count = await post_btn.count()
            if count > 0:
                await post_btn.last.click(force=True)
            else:
                await text_area.press("Control+Return")
            await page.wait_for_timeout(5000)
            print("投稿完了")
            return "posted"

        finally:
            await browser.close()


async def post_thread_to_threads_async(parts: list) -> str:
    """PlaywrightでThreadsにツリー型投稿（複数パート連結）を投稿"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

        if THREADS_SESSION:
            storage = json.loads(base64.b64decode(THREADS_SESSION).decode())
            context = await browser.new_context(user_agent=ua, viewport={"width": 1280, "height": 800}, storage_state=storage)
        else:
            context = await browser.new_context(user_agent=ua, viewport={"width": 1280, "height": 800})

        page = await context.new_page()

        try:
            if THREADS_SESSION:
                await page.goto("https://www.threads.com", wait_until="networkidle", timeout=60000)
                await page.wait_for_timeout(3000)
            else:
                await page.goto("https://www.threads.com/login", wait_until="networkidle", timeout=60000)
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

            await _open_compose(page)

            print(f"ツリー型投稿開始（{len(parts)}パート）")

            # 最初のパートを入力
            text_areas = await page.query_selector_all('[contenteditable="true"]')
            await text_areas[0].click()
            await page.wait_for_timeout(500)
            await page.keyboard.type(parts[0])
            await page.wait_for_timeout(500)

            # 2パート目以降を追加
            for i, part in enumerate(parts[1:], start=2):
                print(f"パート{i}を追加中...")
                # 「スレッドに追加」はテキストDIV（aria-labelなし）
                add_btn = page.get_by_text("スレッドに追加", exact=True)
                try:
                    await add_btn.wait_for(timeout=5000)
                    await add_btn.click()
                    print(f"  「スレッドに追加」クリック成功")
                except Exception as e:
                    print(f"  警告: 「スレッドに追加」が見つかりませんでした（パート{i}をスキップ）: {e}")
                    continue

                await page.wait_for_timeout(1000)
                # 新たに追加されたcontenteditable（最後の1つ）に入力
                text_areas = await page.query_selector_all('[contenteditable="true"]')
                await text_areas[-1].click()
                await page.wait_for_timeout(500)
                await page.keyboard.type(part)
                await page.wait_for_timeout(500)

            print("投稿ボタンを押しています...")
            post_btn = page.get_by_text("投稿", exact=True)
            count = await post_btn.count()
            if count > 0:
                await post_btn.last.click(force=True)
            else:
                text_areas = await page.query_selector_all('[contenteditable="true"]')
                await text_areas[-1].press("Control+Return")
            await page.wait_for_timeout(5000)
            print("ツリー型投稿完了")
            return "posted"

        finally:
            await browser.close()


def post_to_threads(text: str) -> str:
    return asyncio.run(post_to_threads_async(text))


def post_thread_to_threads(parts: list) -> str:
    return asyncio.run(post_thread_to_threads_async(parts))


if __name__ == "__main__":
    test_text = "テスト投稿です #テスト"
    post_id = post_to_threads(test_text)
    print(f"結果: {post_id}")
