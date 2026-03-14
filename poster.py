import asyncio
from playwright.async_api import async_playwright
from config import THREADS_USERNAME, THREADS_PASSWORD


async def post_to_threads_async(text: str) -> str:
    """PlaywrightでThreadsにログインして投稿"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = await context.new_page()

        try:
            # Threadsにアクセス
            await page.goto("https://www.threads.com/login", wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)

            # ログイン
            await page.fill('input[type="text"]', THREADS_USERNAME)
            await page.fill('input[type="password"]', THREADS_PASSWORD)
            await page.click('button[type="submit"]')
            await page.wait_for_timeout(5000)

            # 新規投稿ボタンをクリック
            new_post_btn = await page.query_selector('[aria-label="New post"]')
            if not new_post_btn:
                new_post_btn = await page.query_selector('[aria-label="新しいスレッドを作成"]')
            if not new_post_btn:
                # SVGアイコンのボタンを探す
                new_post_btn = await page.query_selector('svg[aria-label="New post"]')
            if new_post_btn:
                await new_post_btn.click()
            else:
                # ホームに移動して投稿ボタンを探す
                await page.goto("https://www.threads.com", wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(3000)
                new_post_btn = await page.query_selector('[aria-label="New post"]')
                if new_post_btn:
                    await new_post_btn.click()

            await page.wait_for_timeout(2000)

            # テキスト入力
            text_area = await page.query_selector('[contenteditable="true"]')
            if text_area:
                await text_area.click()
                await text_area.fill(text)
            await page.wait_for_timeout(1000)

            # 投稿ボタンをクリック
            post_btn = await page.query_selector('[data-testid="tray-button-post"]')
            if not post_btn:
                post_btn = await page.query_selector('button:has-text("Post")')
            if not post_btn:
                post_btn = await page.query_selector('button:has-text("投稿")')
            if post_btn:
                await post_btn.click()
                await page.wait_for_timeout(5000)
                print("投稿完了")
                return "posted"
            else:
                raise Exception("投稿ボタンが見つかりませんでした")

        finally:
            await browser.close()


def post_to_threads(text: str) -> str:
    return asyncio.run(post_to_threads_async(text))


if __name__ == "__main__":
    test_text = "テスト投稿です #テスト"
    post_id = post_to_threads(test_text)
    print(f"結果: {post_id}")
