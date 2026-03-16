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


async def _type_into_nth_contenteditable(page, index: int, text: str) -> bool:
    """index番目のcontenteditable(0始まり)にテキストを入力しReact stateを更新する。
    click・focus・insertTextを1つのJS評価内で実行することでfocusずれを防ぐ。"""
    return await page.evaluate("""(args) => {
        const {index, text} = args;
        const areas = document.querySelectorAll('[contenteditable="true"]');
        if (index >= areas.length) return false;
        const el = areas[index];
        // フォーカス・クリックをJS内で行う（Playwright非同期ギャップでfocusがずれるのを防ぐ）
        el.focus();
        el.click();
        // insertText: Reactのinputイベントを発火させる
        const ok = document.execCommand('insertText', false, text);
        return ok;
    }""", {"index": index, "text": text})


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

            # パート1を入力（index=0）
            ok = await _type_into_nth_contenteditable(page, 0, parts[0])
            print(f"  パート1入力: {ok}")
            await page.wait_for_timeout(1500)

            # パート2以降を追加
            for i, part in enumerate(parts[1:], start=2):
                print(f"パート{i}を追加中...")

                prev_count = len(await page.query_selector_all('[contenteditable="true"]'))

                # 「Add to thread」をクリック
                clicked = False
                for btn_text in ["Add to thread", "スレッドに追加"]:
                    btn = page.get_by_text(btn_text, exact=True)
                    if await btn.count() > 0:
                        try:
                            await btn.last.scroll_into_view_if_needed()
                            await page.wait_for_timeout(500)
                            await btn.last.click()
                            clicked = True
                            print(f"  クリック: '{btn_text}'")
                            break
                        except Exception as e:
                            print(f"  クリック失敗: {e}")

                if not clicked:
                    print(f"  警告: ボタン未検出（パート{i}スキップ）")
                    continue

                # 新しいcontenteditable が現れるまで待機
                for _ in range(8):
                    await page.wait_for_timeout(500)
                    cur_count = len(await page.query_selector_all('[contenteditable="true"]'))
                    if cur_count > prev_count:
                        break

                # Reactのハンドラマウント完了まで待機してから入力
                await page.wait_for_timeout(1000)
                ok = await _type_into_nth_contenteditable(page, i - 1, part)
                print(f"  パート{i}入力: {ok}")
                await page.wait_for_timeout(1000)

            # 投稿ボタンをクリック
            await page.screenshot(path="/tmp/threads_before_post.png")
            print("投稿ボタンを押しています...")
            posted = False
            for btn_text in ["投稿", "Post"]:
                btn = page.get_by_role("button", name=btn_text, exact=True)
                if await btn.count() > 0:
                    await btn.last.click()
                    posted = True
                    print(f"  '{btn_text}' をクリック")
                    break
            if not posted:
                areas = await page.query_selector_all('[contenteditable="true"]')
                await areas[-1].press("Control+Enter")

            # モーダルが閉じるまで待機
            try:
                await page.wait_for_selector('text="New thread"', state="hidden", timeout=20000)
                print("  モーダルが閉じました")
            except Exception:
                await page.wait_for_timeout(10000)

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
