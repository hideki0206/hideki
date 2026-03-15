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


async def _login_if_needed(page) -> None:
    """セッション切れでログインページに飛んでいた場合にパスワードログインする"""
    if "login" not in page.url and "accounts" not in page.url:
        return
    print(f"セッション切れを検知 (URL: {page.url})。パスワードでログイン中...")
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


async def _open_compose(page) -> None:
    """新規スレッドモーダルを開く"""
    # 現在のURLを確認（セッション切れでログインページに飛んでいないか）
    print(f"現在のURL: {page.url}")
    await page.screenshot(path="/tmp/threads_before_compose.png")

    # 複数のセレクターを順番に試す
    compose_selectors = [
        'text="今なにしてる？"',
        '[aria-label="テキストフィールドが空です。テキストを入力して新しい投稿を作成できます。"]',
        'text="What\'s new?"',
        'text="Start a thread"',
        '[aria-label="New post"]',
        '[aria-label="新しいスレッドを作成"]',
        '[aria-label="Create"]',
        'div[role="button"]:has-text("作成")',
    ]

    opened = False
    for sel in compose_selectors:
        try:
            el = await page.wait_for_selector(sel, timeout=5000)
            if el:
                await el.click()
                print(f"投稿入力欄を開きました: {sel}")
                opened = True
                break
        except Exception:
            continue

    if not opened:
        await page.screenshot(path="/tmp/threads_compose_fail.png")
        raise Exception(f"投稿入力欄が見つかりませんでした。URL: {page.url}")

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
            await page.goto("https://www.threads.com", wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(5000)
            await _login_if_needed(page)

            await _open_compose(page)

            print("テキストを入力中...")
            text_area = await page.wait_for_selector('[contenteditable="true"]', timeout=10000)
            await text_area.click()
            await page.wait_for_timeout(500)
            await page.keyboard.type(text)
            await page.wait_for_timeout(1000)

            print("投稿ボタンを押しています...")
            posted = False
            for btn_text in ["投稿", "Post"]:
                btn = page.get_by_text(btn_text, exact=True)
                count = await btn.count()
                if count > 0:
                    await btn.last.click(force=True)
                    posted = True
                    break
            if not posted:
                await text_area.press("Control+Enter")
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
            await page.goto("https://www.threads.com", wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(5000)
            await _login_if_needed(page)

            await _open_compose(page)

            print(f"ツリー型投稿開始（{len(parts)}パート）")

            # 最初のパートを入力
            text_areas = await page.query_selector_all('[contenteditable="true"]')
            await text_areas[0].click()
            await page.wait_for_timeout(1000)
            await page.keyboard.type(parts[0])
            await page.wait_for_timeout(1500)
            await page.screenshot(path="/tmp/threads_part1.png")

            # 2パート目以降を追加
            for i, part in enumerate(parts[1:], start=2):
                print(f"パート{i}を追加中...")

                # 現在のcontenteditable数を確認
                text_areas = await page.query_selector_all('[contenteditable="true"]')
                print(f"  現在のcontenteditable数: {len(text_areas)}")

                # JavaScriptで「Add to thread」「スレッドに追加」を含む要素をクリック
                # スクロールしてから dispatch click（最後に出現する要素を対象）
                clicked = await page.evaluate("""() => {
                    const keywords = ['Add to thread', 'スレッドに追加'];
                    const walker = document.createTreeWalker(
                        document.body, NodeFilter.SHOW_TEXT, null, false
                    );
                    let found = null;
                    let node;
                    while ((node = walker.nextNode())) {
                        const txt = node.textContent.trim();
                        if (keywords.some(kw => txt === kw)) {
                            found = {node, txt};
                        }
                    }
                    if (found) {
                        const el = found.node.parentElement;
                        el.scrollIntoView({behavior: 'instant', block: 'center'});
                        el.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}));
                        return found.txt;
                    }
                    return null;
                }""")

                if clicked:
                    print(f"  JS クリック成功: '{clicked}'")
                    # 新しいcontenteditable が追加されるまで待機
                    await page.wait_for_timeout(1500)
                    text_areas = await page.query_selector_all('[contenteditable="true"]')
                    print(f"  クリック後のcontenteditable数: {len(text_areas)}")
                    await text_areas[-1].click()
                    await page.wait_for_timeout(500)
                    await page.keyboard.type(part)
                    await page.wait_for_timeout(500)
                else:
                    await page.screenshot(path=f"/tmp/threads_part{i}_fail.png")
                    texts = await page.evaluate("""() => {
                        const els = document.querySelectorAll('div[role="button"], button, [contenteditable]');
                        return Array.from(els).map(e => e.textContent.trim().substring(0, 50)).filter(t => t);
                    }""")
                    print(f"  警告: 「スレッドに追加」未検出（パート{i}スキップ）。ページ要素: {texts[:20]}")
                    continue

            await page.screenshot(path="/tmp/threads_before_post.png")
            print("投稿ボタンを押しています...")

            # 投稿ボタン: 日本語「投稿」または英語「Post」
            posted = False
            for btn_text in ["投稿", "Post"]:
                btn = page.get_by_text(btn_text, exact=True)
                count = await btn.count()
                if count > 0:
                    await btn.last.click(force=True)
                    posted = True
                    print(f"  投稿ボタン '{btn_text}' をクリック")
                    break

            if not posted:
                text_areas = await page.query_selector_all('[contenteditable="true"]')
                await text_areas[-1].press("Control+Enter")
                print("  Control+Enter で投稿")

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
